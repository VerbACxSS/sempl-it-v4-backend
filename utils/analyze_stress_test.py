import argparse
import asyncio
import time

import httpx


URL = "http://localhost:30010/api/v1/analyze/text"

TEXT = """
Il Comune di Valle Serena intende sostenere gli interventi destinati alla riduzione dei consumi energetici degli edifici aperti al pubblico, con particolare attenzione alle scuole, alle biblioteche e ai centri civici situati nelle frazioni. A tale scopo, l'Amministrazione ha previsto un programma di contributi rivolto agli enti, alle associazioni senza scopo di lucro e ai soggetti che gestiscono servizi di interesse collettivo. Le risorse disponibili saranno assegnate in base alla qualità tecnica delle proposte, alla loro concreta realizzabilità e alla capacità di produrre benefici verificabili nel tempo.

La domanda deve essere presentata esclusivamente attraverso il portale istituzionale entro le ore dodici del giorno indicato nell'avviso. Il richiedente è tenuto a compilare ogni sezione del modulo, a descrivere con precisione l'intervento proposto e ad allegare il preventivo di spesa, il cronoprogramma e la documentazione che dimostri la disponibilità dell'immobile. Qualora il progetto riguardi un edificio utilizzato da più soggetti, dovrà essere indicato il responsabile incaricato di coordinare le attività e di mantenere i rapporti con gli uffici comunali.

L'istruttoria sarà svolta dal servizio lavori pubblici, che potrà richiedere chiarimenti, integrazioni documentali o un sopralluogo quando le informazioni trasmesse non consentano di valutare adeguatamente il progetto. La richiesta di integrazione sospende il termine del procedimento e dovrà essere riscontrata entro dieci giorni; trascorso inutilmente tale periodo, la domanda potrà essere archiviata. Non saranno considerate ammissibili le spese sostenute prima della pubblicazione dell'avviso, salvo quelle strettamente necessarie alla redazione della diagnosi energetica.

Per ogni proposta ammessa, una commissione attribuirà un punteggio considerando il risparmio stimato, la riduzione delle emissioni, la coerenza con il piano comunale per il clima e l'accessibilità degli spazi interessati. Sarà riconosciuta priorità agli interventi che prevedono la sostituzione di impianti obsoleti, l'installazione di sistemi di monitoraggio e il coinvolgimento degli utenti attraverso attività informative. In caso di parità di punteggio, sarà preferita la domanda presentata dal soggetto che dimostri una maggiore capacità di cofinanziamento.

L'eventuale concessione del contributo non comporta l'immediata erogazione dell'intera somma. Dopo la comunicazione di ammissione, il beneficiario dovrà accettare le condizioni previste, avviare le attività entro il termine stabilito e conservare fatture, contratti e attestazioni di pagamento. Al termine dei lavori dovrà essere inviata una relazione conclusiva, corredata da fotografie e da un riepilogo delle spese. Il Comune potrà effettuare controlli successivi e, qualora emergano irregolarità sostanziali oppure un utilizzo delle risorse diverso da quello autorizzato, potrà disporre la revoca totale o parziale del contributo.

Nel corso della realizzazione, il beneficiario dovrà comunicare senza ritardo ogni circostanza che possa incidere sul costo, sui tempi o sulla finalità dell'intervento. Le modifiche non sostanziali potranno essere autorizzate dal responsabile del procedimento, purché non riducano il risultato atteso; le variazioni più rilevanti richiederanno invece una nuova valutazione. Per garantire trasparenza, l'elenco dei progetti finanziati, l'importo concesso e lo stato di avanzamento saranno pubblicati nella sezione dedicata del sito comunale, nel rispetto delle disposizioni sulla protezione dei dati personali.

La domanda implica l'accettazione delle regole del programma e l'impegno a collaborare con il Comune nelle eventuali attività di verifica. L'Amministrazione si riserva di aggiornare le modalità operative qualora intervengano norme nuove, esigenze organizzative o circostanze che rendano necessario assicurare una più efficace gestione delle risorse pubbliche.
""".strip()

assert len(TEXT) <= 4000


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

    limits = httpx.Limits(
        max_connections=number_of_requests,
        max_keepalive_connections=number_of_requests,
    )

    timeout = httpx.Timeout(600.0)

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
        start_event.set()

        results = await asyncio.gather(*tasks)

        total_duration = time.perf_counter() - global_start

    successful = [
        result for result in results
        if result["status"] is not None and 200 <= result["status"] < 300
    ]

    failed = [
        result for result in results
        if result["status"] is None or not (200 <= result["status"] < 300)
    ]

    durations = [result["duration"] for result in results]

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
        description="Concurrent Sempl-it text analysis stress test"
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
