import argparse
import asyncio
import random
import time
from collections import Counter
from pathlib import Path
import csv
import httpx

SIMPLIFY_URL = "http://localhost:30010/api/v1/simplify/"
ANALYZE_URL = "http://localhost:30010/api/v1/analyze/text"
COMPARE_URL = "http://localhost:30010/api/v1/analyze/comparison"

SIMPLIFY_URL = "http://localhost:30010/api/v1/simplify/"
ANALYZE_URL = "http://localhost:30010/api/v1/analyze/text"
COMPARE_URL = "http://localhost:30010/api/v1/analyze/comparison"

FUNCTIONS = ("SIMPLIFY", "ANALYZE", "COMPARE")

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


def request_spec(
    kind: str,
    text1: str,
    text2: str | None = None,
):
    if kind == "SIMPLIFY":
        return (
            SIMPLIFY_URL,
            {
                "text": text1,
                "target": "common",
                "consent": False,
            },
        )
    if kind == "ANALYZE":
        return (
            ANALYZE_URL,
            {
                "text": text1,
                "consent": False,
            },
        )
    if kind == "COMPARE":
        if text2 is None:
            raise ValueError("COMPARE requires two texts")
        return (
            COMPARE_URL,
            {
                "text1": text1,
                "text2": text2,
                "consent": False,
            },
        )
    raise ValueError(f"Unknown request type: {kind}")


async def send_mixed_request(
    client: httpx.AsyncClient,
    request_number: int,
    kind: str,
    row1: int,
    text1: str,
    row2: int | None,
    text2: str | None,
    session_start: float,
    active_lock: asyncio.Lock,
    active_state: dict,
):
    url, payload = request_spec(kind, text1, text2)
    started = time.perf_counter()
    start_offset = started - session_start

    async with active_lock:
        active_state["current"] += 1
        active_state["peak"] = max(
            active_state["peak"],
            active_state["current"],
        )
        active_at_start = active_state["current"]

    source = (
        f"row={row1}"
        if kind != "COMPARE"
        else f"row1={row1} row2={row2}"
    )

    print(
        f"[{request_number:03d}] START {kind:<8} "
        f"{source} at=+{start_offset:.2f}s "
        f"active={active_at_start}"
    )

    status = None
    error = None

    try:
        response = await client.post(url, json=payload)
        status = response.status_code
    except Exception as exc:
        error = str(exc)

    duration = time.perf_counter() - started

    async with active_lock:
        active_state["current"] -= 1
        active_after = active_state["current"]

    status_text = status if status is not None else "ERROR"
    print(
        f"[{request_number:03d}] END   {kind:<8} "
        f"{source} status={status_text} "
        f"duration={duration:.2f}s active={active_after}"
    )

    return {
        "number": request_number,
        "kind": kind,
        "row1": row1,
        "row2": row2,
        "status": status,
        "duration": duration,
        "start_offset": start_offset,
        "error": error,
    }


async def main(
    number_of_requests: int,
    csv_filename: str,
    min_interval: float,
    max_interval: float,
    seed: int | None,
):
    csv_path = Path(csv_filename)

    try:
        rows, _ = load_csv(csv_path)

        if number_of_requests < 1:
            raise ValueError("requests must be >= 1")
        if number_of_requests > MAX_REQUESTS:
            raise ValueError(f"requests must be <= {MAX_REQUESTS}")
        if len(rows) < 2:
            raise ValueError(
                "CSV must contain at least 2 rows "
                "to support COMPARE requests"
            )
        if min_interval < 0:
            raise ValueError("min-interval must be >= 0")
        if max_interval < min_interval:
            raise ValueError(
                "max-interval must be >= min-interval"
            )

        # Validate the full CSV because any row can be selected randomly.
        errors = []
        lengths = []
        for index, row in enumerate(rows, start=1):
            text = row.get("testo", "") or ""
            lengths.append(len(text))
            if not text.strip():
                errors.append(f"Row {index}: empty text")
            elif len(text) > MAX_TEXT_LENGTH:
                errors.append(
                    f"Row {index}: {len(text)} characters "
                    f"(max {MAX_TEXT_LENGTH})"
                )

        if errors:
            raise ValueError(
                "Invalid CSV inputs:\n" + "\n".join(errors)
            )

    except (FileNotFoundError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        return

    rng = random.Random(seed)

    # Pre-generate the whole session from the same RNG.
    # Same seed => same functions, rows and arrival intervals.
    plan = []
    for request_number in range(1, number_of_requests + 1):
        kind = rng.choice(FUNCTIONS)

        row1_index = rng.randrange(len(rows))
        row2_index = None

        if kind == "COMPARE":
            # Always choose two distinct CSV rows.
            candidates = [
                i for i in range(len(rows))
                if i != row1_index
            ]
            row2_index = rng.choice(candidates)

        plan.append({
            "number": request_number,
            "kind": kind,
            "row1_index": row1_index,
            "row2_index": row2_index,
        })

    intervals = [
        rng.uniform(min_interval, max_interval)
        for _ in range(max(0, number_of_requests - 1))
    ]

    planned = Counter(item["kind"] for item in plan)

    print("--- REALISTIC MIXED TRAFFIC TEST ---")
    print(f"CSV:               {csv_path}")
    print(f"CSV rows:          {len(rows)}")
    print(f"Requests:          {number_of_requests}")
    print(
        f"Arrival interval:  {min_interval:.2f}s - "
        f"{max_interval:.2f}s"
    )
    print(
        f"Seed:              "
        f"{seed if seed is not None else 'random'}"
    )
    print(
        "Planned mix:       "
        f"SIMPLIFY={planned['SIMPLIFY']}, "
        f"ANALYZE={planned['ANALYZE']}, "
        f"COMPARE={planned['COMPARE']}"
    )
    print(
        f"CSV text length:   min={min(lengths)}, "
        f"avg={sum(lengths)/len(lengths):.2f}, "
        f"max={max(lengths)} chars"
    )
    print("CSV mode:          READ-ONLY")
    print()

    limits = httpx.Limits(
        max_connections=number_of_requests,
        max_keepalive_connections=number_of_requests,
    )
    timeout = httpx.Timeout(1200.0)

    active_lock = asyncio.Lock()
    active_state = {"current": 0, "peak": 0}
    tasks = []

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
    ) as client:
        session_start = time.perf_counter()

        for position, item in enumerate(plan):
            if position > 0:
                delay = intervals[position - 1]
                print(
                    f"Next request #{item['number']:03d} "
                    f"({item['kind']}) in {delay:.2f}s"
                )
                await asyncio.sleep(delay)

            r1 = item["row1_index"]
            r2 = item["row2_index"]

            tasks.append(
                asyncio.create_task(
                    send_mixed_request(
                        client=client,
                        request_number=item["number"],
                        kind=item["kind"],
                        row1=r1 + 1,
                        text1=rows[r1]["testo"],
                        row2=(r2 + 1) if r2 is not None else None,
                        text2=(
                            rows[r2]["testo"]
                            if r2 is not None
                            else None
                        ),
                        session_start=session_start,
                        active_lock=active_lock,
                        active_state=active_state,
                    )
                )
            )

        last_arrival = time.perf_counter() - session_start
        print(
            "\nAll requests submitted. "
            "Waiting for outstanding requests...\n"
        )

        results = await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - session_start

    successful = [
        r for r in results
        if r["status"] is not None
        and 200 <= r["status"] < 300
    ]
    failed = [
        r for r in results
        if r["status"] is None
        or not (200 <= r["status"] < 300)
    ]

    print("\n--- REQUEST DETAILS ---")
    for r in results:
        status = (
            r["status"]
            if r["status"] is not None
            else "ERROR"
        )
        source = (
            f"row={r['row1']}"
            if r["kind"] != "COMPARE"
            else f"row1={r['row1']} row2={r['row2']}"
        )
        print(
            f"#{r['number']:03d} {r['kind']:<8} "
            f"{source:<18} "
            f"start=+{r['start_offset']:.2f}s "
            f"duration={r['duration']:.2f}s "
            f"status={status}"
        )

    print("\n--- SESSION SUMMARY ---")
    print(f"Requests:                 {number_of_requests}")
    print(f"Successful:               {len(successful)}")
    print(f"Failed:                   {len(failed)}")
    print(f"Last request arrived at:  +{last_arrival:.2f}s")
    print(f"Total session time:       {total_duration:.2f}s")
    print(
        f"Peak concurrent requests: "
        f"{active_state['peak']}"
    )

    if intervals:
        print(
            f"Min arrival interval:     "
            f"{min(intervals):.2f}s"
        )
        print(
            f"Average arrival interval: "
            f"{sum(intervals)/len(intervals):.2f}s"
        )
        print(
            f"Max arrival interval:     "
            f"{max(intervals):.2f}s"
        )

    print("\n--- SUMMARY BY FUNCTION ---")
    for kind in FUNCTIONS:
        subset = [
            r for r in results
            if r["kind"] == kind
        ]

        if not subset:
            print(f"{kind:<8} requests=0")
            continue

        ok = [
            r for r in subset
            if r["status"] is not None
            and 200 <= r["status"] < 300
        ]
        durations = [r["duration"] for r in subset]

        print(
            f"{kind:<8} "
            f"requests={len(subset)} "
            f"success={len(ok)} "
            f"failed={len(subset)-len(ok)} "
            f"min={min(durations):.2f}s "
            f"avg={sum(durations)/len(durations):.2f}s "
            f"max={max(durations):.2f}s"
        )

    if failed:
        print("\n--- FAILURES ---")
        for r in failed:
            print(
                f"#{r['number']:03d} {r['kind']:<8} "
                f"status={r['status']} "
                f"error={r['error']}"
            )

    print(
        "\nCSV was used as read-only input; "
        "no rows or result columns were modified."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Realistic read-only Sempl-it traffic simulation "
            "across Simplify, Analyze and Compare"
        )
    )
    parser.add_argument(
        "requests",
        type=int,
        help=(
            "Total number of requests in the simulated "
            "session (1-100)"
        ),
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=f"Input CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=1.0,
        help=(
            "Minimum interval between arrivals "
            "in seconds (default: 1)"
        ),
    )
    parser.add_argument(
        "--max-interval",
        type=float,
        default=60.0,
        help=(
            "Maximum interval between arrivals "
            "in seconds (default: 60)"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Seed controlling function selection, "
            "CSV rows and arrival timing"
        ),
    )

    args = parser.parse_args()

    if args.requests < 1:
        parser.error("requests must be >= 1")
    if args.requests > MAX_REQUESTS:
        parser.error(
            f"requests must be <= {MAX_REQUESTS}"
        )

    asyncio.run(
        main(
            args.requests,
            args.csv,
            args.min_interval,
            args.max_interval,
            args.seed,
        )
    )
