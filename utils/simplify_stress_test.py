import argparse
import asyncio
import time

import httpx


URL = "http://localhost:30010/api/v1/simplify/"

TEXT = """Ai sensi della normativa vigente e delle disposizioni applicabili in materia di sostegno alle attività economiche, le imprese interessate alla concessione del contributo per l’acquisto di attrezzature e servizi destinati alla digitalizzazione possono presentare domanda tramite la procedura telematica disponibile sul portale istituzionale. La domanda, corredata dalla documentazione richiesta, dovrà essere trasmessa entro il termine indicato nell’avviso, secondo le modalità previste, per consentire all’Ufficio competente lo svolgimento dell’istruttoria e la verifica dei requisiti dichiarati.

La presentazione della domanda non comporta automaticamente il riconoscimento del contributo. L’agevolazione potrà essere concessa nei limiti delle risorse disponibili e a condizione che siano rispettati i requisiti eventualmente previsti dalle disposizioni applicabili. Qualora le risorse non siano sufficienti per tutte le richieste ammissibili, si procederà secondo i criteri stabiliti nell’avviso. Il possesso dei requisiti non determina, di per sé, il diritto all’erogazione del contributo.

Durante l’istruttoria, qualora venga rilevata dall’Ufficio la presenza di informazioni incomplete, dichiarazioni non coerenti o documenti non leggibili, il procedimento potrà essere sospeso. Il richiedente, ove previsto, sarà informato mediante apposita comunicazzione e potrà essere invitato a fornire chiarimenti o a integrare la documentazione. L’integrazione dovrà avvenire entro dieci giorni dalla ricezione della comunicazione, salvo che nella stessa sia indicato un termine diverso in conformità alle disposizioni applicabili.

La ricezione della comunicazione non comporta l’accertamento definitivo della mancanza dei requisiti e la trasmissione dei documenti integrativi non determina automaticamente l’accoglimento della domanda. L’Ufficio valuterà la documentazione acquisita nell’ambito dell’istruttoria. Non sono ammesse integrazioni con modalità diverse da quelle eventualmente indicate nella comunicazione, salvo i casi previsti dalla normativa applicabile.

In caso di mancata trasmissione della documentazione entro il termine assegnato, l’Ufficio potrà procedere all’archiviazzione della domanda, qualora ne ricorrano i presupposti. L’archiviazione sarà comunicata all’interessato. Resta ferma, ove consentito dalle disposizioni applicabili, la possibilità di presentare una nuova domanda, purché il termine dell’avviso non sia scaduto e siano ancora disponibili le risorse. La nuova domanda sarà sottoposta a una nuova istruttoria e non beneficierà automaticamente delle verifiche effettuate sulla precedente.

Qualora la nuova domanda sia presentata, l’Amministrazione potrà richiedere nuovamente documenti già trasmessi, ove ciò risulti necessario per le verifiche previste. La precedente presentazione dei documenti non esonera il richiedente dagli adempimenti eventualmente richiesti nell’ambito della nuova istruttoria.

Conclusa l’istruttoria, l’Ufficio competente adotterà il provvedimento previsto. In caso di esito favorevole, l’erogazione del contributo potrà essere subordinata a ulteriori verifiche previste dalla normativa vigente. Il richiedente dovrà mantenere, per il periodo eventualmente stabilito dalle disposizioni applicabili, le condizioni richieste per beneficiare dell’agevolazione. La perdita di tali condizioni potrà comportare i provvedimenti previsti dalla normativa.

I beneficiari devono conservare la documentazione relativa alle spese sostenute e, ove richiesto, renderla disponibile per i controlli degli uffici competenti. La conservazzione dovrà avvenire per il periodo previsto dalle disposizioni applicabili.

Eventuali variazioni rilevanti successive alla domanda dovranno essere comunicate all’Amministrazione nei casi e secondo le modalità previste dalle disposizioni applicabili. La comunicazione di una variazione non comporta automaticamente la modifica, la revoca o la conferma del beneficio eventualmente riconosciuto."""


async def send_request(
    client: httpx.AsyncClient,
    request_number: int,
    start_event: asyncio.Event,
):
    await start_event.wait()

    started = time.perf_counter()

    try:
        response = await client.post(
            URL,
            json={
                "text": TEXT,
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

        return {
            "number": request_number,
            "status": response.status_code,
            "duration": duration,
            "error": None,
        }

    except Exception as exc:
        duration = time.perf_counter() - started

        print(
            f"[{request_number:02d}] "
            f"ERROR after {duration:.2f}s: {exc}"
        )

        return {
            "number": request_number,
            "status": None,
            "duration": duration,
            "error": str(exc),
        }


async def main(number_of_requests: int):
    print(f"Target: {URL}")
    print(f"Requests: {number_of_requests}")
    print(f"Text length: {len(TEXT)} characters")
    print()

    # Nessun limite artificiale introdotto dal client.
    limits = httpx.Limits(
        max_connections=number_of_requests,
        max_keepalive_connections=number_of_requests,
    )

    timeout = httpx.Timeout(1200.0)

    start_event = asyncio.Event()

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
    ) as client:

        tasks = [
            asyncio.create_task(
                send_request(client, i, start_event)
            )
            for i in range(1, number_of_requests + 1)
        ]

        print("All requests ready. Starting simultaneously...\n")

        global_start = time.perf_counter()

        # Tutte le coroutine vengono sbloccate insieme.
        start_event.set()

        results = await asyncio.gather(*tasks)

        total_duration = time.perf_counter() - global_start

    successful = [
        r for r in results
        if r["status"] is not None and 200 <= r["status"] < 300
    ]

    failed = [
        r for r in results
        if r["status"] is None or not (200 <= r["status"] < 300)
    ]

    durations = [r["duration"] for r in results]

    print("\n--- SUMMARY ---")
    print(f"Requests:   {number_of_requests}")
    print(f"Successful: {len(successful)}")
    print(f"Failed:     {len(failed)}")
    print(f"Total time: {total_duration:.2f}s")

    if durations:
        print(f"Fastest:    {min(durations):.2f}s")
        print(f"Slowest:    {max(durations):.2f}s")
        print(
            f"Average:    "
            f"{sum(durations) / len(durations):.2f}s"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Concurrent Sempl-it simplification stress test"
    )

    parser.add_argument(
        "requests",
        type=int,
        help="Number of concurrent requests",
    )

    args = parser.parse_args()

    if args.requests < 1:
        parser.error("requests must be >= 1")

    asyncio.run(main(args.requests))