import argparse
import asyncio
import csv
import time
from pathlib import Path

import httpx


URL = "http://localhost:30010/api/v1/simplify/"
DEFAULT_CSV = "sempl_it_test_texts.csv"
MAX_REQUESTS = 100
MAX_TEXT_LENGTH = 4000

STEP_COLUMNS = [
    "proofreading",
    "lex",
    "connectives",
    "expressions",
    "sentence_splitter",
    "nominalizations",
    "verbs",
    "sentence_reorganizer",
    "explain",
]

RESULT_COLUMNS = STEP_COLUMNS + [
    "status",
    "duration_seconds",
]


def load_csv(csv_path: Path):
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        fieldnames = list(reader.fieldnames)

        if "testo" not in fieldnames:
            raise ValueError(
                "CSV must contain a 'testo' column"
            )

        rows = list(reader)

    for column in RESULT_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)

    for row in rows:
        for column in RESULT_COLUMNS:
            row.setdefault(column, "")

    return rows, fieldnames


def validate_inputs(rows, number_of_requests):
    """
    Valida TUTTI gli input prima che venga effettuata
    qualsiasi richiesta HTTP.
    """

    if number_of_requests < 1:
        raise ValueError("requests must be >= 1")

    if number_of_requests > MAX_REQUESTS:
        raise ValueError(
            f"requests must be <= {MAX_REQUESTS}"
        )

    if number_of_requests > len(rows):
        raise ValueError(
            f"Requested {number_of_requests} documents, "
            f"but CSV contains only {len(rows)} rows"
        )

    selected_rows = rows[:number_of_requests]

    errors = []
    lengths = []

    for index, row in enumerate(selected_rows, start=1):
        text = row.get("testo", "")

        if text is None:
            text = ""

        text_length = len(text)
        lengths.append(text_length)

        if not text.strip():
            errors.append(
                f"Row {index}: empty text"
            )
            continue

        if text_length > MAX_TEXT_LENGTH:
            errors.append(
                f"Row {index}: "
                f"{text_length} characters "
                f"(max {MAX_TEXT_LENGTH})"
            )

    if errors:
        print("\nINPUT VALIDATION FAILED")
        print("-----------------------")

        for error in errors:
            print(error)

        print(
            "\nAborting before sending any HTTP request."
        )

        raise ValueError(
            f"{len(errors)} invalid input(s)"
        )

    return lengths


def write_csv(
    csv_path: Path,
    rows,
    fieldnames,
):
    """
    Riscrive il CSV completo.

    Le righe non coinvolte nel test vengono mantenute
    esattamente nel dataset.
    """

    temp_path = csv_path.with_suffix(
        csv_path.suffix + ".tmp"
    )

    with temp_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(csv_path)


async def save_result(
    csv_path: Path,
    rows,
    fieldnames,
    row_index: int,
    result,
    write_lock: asyncio.Lock,
):
    async with write_lock:
        row = rows[row_index]
        
        for step in STEP_COLUMNS:
            row[step] = result["steps"].get(step, "")

        row["status"] = (
            result["status"]
            if result["status"] is not None
            else "ERROR"
        )

        row["duration_seconds"] = (
            f"{result['duration']:.2f}"
        )

        write_csv(
            csv_path,
            rows,
            fieldnames,
        )


async def send_request(
    client: httpx.AsyncClient,
    request_number: int,
    row_index: int,
    text: str,
    start_event: asyncio.Event,
    csv_path: Path,
    rows,
    fieldnames,
    write_lock: asyncio.Lock,
):
    await start_event.wait()

    started = time.perf_counter()

    try:
        response = await client.post(
            URL,
            json={
                "text": text,
                "target": "common",
                "consent": False,
            },
        )

        duration = time.perf_counter() - started

        print(
            f"[{request_number:02d}] "
            f"status={response.status_code} "
            f"duration={duration:.2f}s"
        )

        steps = {}

        if 200 <= response.status_code < 300:
            try:
                payload = response.json()

                simplification_steps = payload.get(
                    "simplificationSteps",
                    {},
                )

                for step in STEP_COLUMNS:
                    steps[step] = (
                        simplification_steps.get(
                            step,
                            "",
                        )
                    )

            except Exception as exc:
                print(
                    f"[{request_number:02d}] "
                    f"WARNING: could not parse response: "
                    f"{exc}"
                )

        result = {
            "number": request_number,
            "status": response.status_code,
            "duration": duration,
            "error": None,
            "steps": steps,
        }

        await save_result(
            csv_path,
            rows,
            fieldnames,
            row_index,
            result,
            write_lock,
        )

        return result

    except Exception as exc:
        duration = time.perf_counter() - started

        print(
            f"[{request_number:02d}] "
            f"ERROR after {duration:.2f}s: {exc}"
        )

        result = {
            "number": request_number,
            "status": None,
            "duration": duration,
            "error": str(exc),
            "steps": {},
        }

        await save_result(
            csv_path,
            rows,
            fieldnames,
            row_index,
            result,
            write_lock,
        )

        return result


async def main(
    number_of_requests: int,
    csv_filename: str,
):
    csv_path = Path(csv_filename)

    try:
        rows, fieldnames = load_csv(csv_path)

        lengths = validate_inputs(
            rows,
            number_of_requests,
        )

    except (FileNotFoundError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        return

    average_length = sum(lengths) / len(lengths)

    print(f"Target: {URL}")
    print(f"CSV: {csv_path}")
    print(f"Requests: {number_of_requests}")
    print()

    print("--- INPUT VALIDATION ---")
    print(f"Documents:      {number_of_requests}")
    print(
        f"Min length:     "
        f"{min(lengths)} characters"
    )
    print(
        f"Max length:     "
        f"{max(lengths)} characters"
    )
    print(
        f"Average length: "
        f"{average_length:.2f} characters"
    )
    print(
        f"All documents valid "
        f"(<= {MAX_TEXT_LENGTH} characters)."
    )
    print()

    limits = httpx.Limits(
        max_connections=number_of_requests,
        max_keepalive_connections=number_of_requests,
    )

    timeout = httpx.Timeout(1200.0)

    start_event = asyncio.Event()
    write_lock = asyncio.Lock()

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
    ) as client:

        tasks = [
            asyncio.create_task(
                send_request(
                    client=client,
                    request_number=i,
                    row_index=i - 1,
                    text=rows[i - 1]["testo"],
                    start_event=start_event,
                    csv_path=csv_path,
                    rows=rows,
                    fieldnames=fieldnames,
                    write_lock=write_lock,
                )
            )
            for i in range(
                1,
                number_of_requests + 1,
            )
        ]

        print(
            "All requests ready. "
            "Starting simultaneously...\n"
        )

        global_start = time.perf_counter()

        start_event.set()

        results = await asyncio.gather(*tasks)

        total_duration = (
            time.perf_counter() - global_start
        )

    successful = [
        r
        for r in results
        if (
            r["status"] is not None
            and 200 <= r["status"] < 300
        )
    ]

    failed = [
        r
        for r in results
        if (
            r["status"] is None
            or not (200 <= r["status"] < 300)
        )
    ]

    durations = [
        r["duration"]
        for r in results
    ]

    print("\n--- SUMMARY ---")
    print(
        f"Requests:            "
        f"{number_of_requests}"
    )
    print(
        f"Average text length: "
        f"{average_length:.2f} characters"
    )
    print(
        f"Successful:          "
        f"{len(successful)}"
    )
    print(
        f"Failed:              "
        f"{len(failed)}"
    )
    print(
        f"Total time:          "
        f"{total_duration:.2f}s"
    )

    if durations:
        print(
            f"Fastest:             "
            f"{min(durations):.2f}s"
        )
        print(
            f"Slowest:             "
            f"{max(durations):.2f}s"
        )
        print(
            f"Average duration:    "
            f"{sum(durations) / len(durations):.2f}s"
        )

    print(
        f"CSV updated:         "
        f"{csv_path}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Concurrent Sempl-it CSV "
            "simplification stress test"
        )
    )

    parser.add_argument(
        "requests",
        type=int,
        help=(
            "Number of CSV rows to process "
            "(1-100)"
        ),
    )

    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=(
            "CSV file to process "
            f"(default: {DEFAULT_CSV})"
        ),
    )

    args = parser.parse_args()

    if args.requests < 1:
        parser.error(
            "requests must be >= 1"
        )

    if args.requests > MAX_REQUESTS:
        parser.error(
            f"requests must be <= {MAX_REQUESTS}"
        )

    asyncio.run(
        main(
            args.requests,
            args.csv,
        )
    )