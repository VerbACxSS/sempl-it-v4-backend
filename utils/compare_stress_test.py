import argparse
import asyncio
import time

import httpx


URL = "http://localhost:30010/api/v1/analyze/comparison"

REFERENCE_TEXT = """
Il Comune di Valle Serena ha approvato un programma per migliorare la sicurezza e l'accessibilità degli spazi pubblici situati nel centro storico e nelle frazioni. Il programma riguarda, tra gli altri interventi, la sistemazione dei percorsi pedonali, l'adeguamento dell'illuminazione, la rimozione delle barriere architettoniche e la realizzazione di segnaletica comprensibile anche dalle persone con difficoltà sensoriali. L'Amministrazione intende procedere in modo graduale, tenendo conto delle esigenze espresse dai residenti, dalle attività commerciali e dalle associazioni che operano sul territorio.

Prima di definire il progetto esecutivo, gli uffici raccoglieranno osservazioni e proposte attraverso incontri pubblici, questionari online e colloqui con i rappresentanti dei quartieri. I contributi ricevuti saranno valutati insieme alle indicazioni contenute nel piano urbano della mobilità e nei documenti relativi alla tutela del patrimonio storico. Poiché alcune strade presentano vincoli paesaggistici e una conformazione particolarmente stretta, le soluzioni tecniche dovranno essere compatibili con il contesto, senza tuttavia rinunciare agli obiettivi di sicurezza e di fruibilità.

Il progetto preliminare dovrà indicare le aree interessate, le opere previste, i materiali da utilizzare, il costo stimato e le possibili interferenze con i sottoservizi esistenti. Sarà inoltre necessario descrivere le misure adottate per limitare i disagi durante il cantiere, soprattutto nei periodi di maggiore affluenza turistica e in prossimità delle scuole. Qualora siano necessari spostamenti temporanei della viabilità o modifiche alle fermate del trasporto pubblico, il gestore del servizio e la polizia locale dovranno essere coinvolti con adeguato anticipo.

Le proposte saranno esaminate da un gruppo di lavoro composto da tecnici comunali, esperti di accessibilità e rappresentanti degli enti competenti. La valutazione considererà la durata delle opere, la manutenzione prevista, la riduzione dei rischi per pedoni e ciclisti, nonché la capacità dell'intervento di collegare luoghi frequentati quotidianamente, come l'ambulatorio, la scuola e gli uffici pubblici. Qualora le risorse disponibili non siano sufficienti a finanziare tutte le opere, verranno realizzati per primi gli interventi considerati più urgenti.

Dopo l'approvazione del progetto, il Comune pubblicherà un calendario dei lavori e comunicherà le modifiche temporanee alla circolazione. Durante l'esecuzione saranno effettuati controlli periodici per verificare la conformità delle opere e l'osservanza delle norme di sicurezza. Al termine, una relazione illustrerà i risultati raggiunti, le eventuali variazioni rispetto al progetto iniziale e le attività di manutenzione necessarie affinché gli spazi riqualificati restino accessibili e sicuri nel corso degli anni.

Per l'affidamento delle opere saranno applicate le procedure previste dalla normativa vigente, con particolare attenzione alla qualità dei materiali, all'esperienza delle imprese e alla capacità di rispettare le scadenze. Il capitolato dovrà includere indicazioni chiare sulla protezione dei passaggi pedonali, sulla gestione delle polveri e dei rumori e sul ripristino delle aree interessate. Qualora durante i lavori emergano problemi imprevisti, il responsabile del procedimento valuterà le soluzioni possibili insieme alla direzione dei lavori, documentando le decisioni assunte.

L'Amministrazione si impegna inoltre a monitorare l'utilizzo degli spazi dopo la conclusione degli interventi, raccogliendo segnalazioni e dati utili a verificare se le opere abbiano effettivamente migliorato gli spostamenti quotidiani. I risultati saranno condivisi con i quartieri e potranno orientare le scelte future. In questo modo, la riqualificazione non sarà considerata un'azione isolata, ma parte di un percorso continuo nel quale manutenzione, ascolto dei cittadini e programmazione delle risorse restano strettamente collegati.
""".strip()

SIMPLIFIED_TEXT = """
Il Comune di Valle Serena vuole rendere più sicuri e più facili da usare gli spazi pubblici del centro e delle frazioni. Il piano riguarda i marciapiedi, le luci delle strade, le rampe per chi usa una sedia a rotelle e i cartelli utili anche a chi vede o sente con difficoltà. I lavori saranno fatti a poco a poco. Prima di scegliere le priorità, il Comune ascolterà le persone che abitano nella zona, i negozi e le associazioni locali.

Gli uffici comunali chiederanno idee e osservazioni con incontri aperti, questionari sul sito e colloqui con i rappresentanti dei quartieri. Le proposte saranno confrontate con il piano della mobilità e con le regole che proteggono gli edifici e le strade storiche. Alcune vie sono strette o hanno vincoli particolari; per questo le soluzioni dovranno rispettare il luogo, ma dovranno anche permettere a tutti di muoversi con maggiore sicurezza.

Il primo progetto indicherà dove si lavorerà, quali opere saranno realizzate, quali materiali serviranno e quanto potrebbero costare. Dovrà anche spiegare come ridurre i problemi per residenti, visitatori e attività durante il cantiere. Se sarà necessario cambiare per un periodo il percorso delle auto, degli autobus o dei pedoni, il Comune avviserà per tempo la polizia locale, il gestore dei trasporti e le persone interessate.

Un gruppo formato da tecnici comunali, esperti di accessibilità e altri enti esaminerà le proposte. Saranno preferiti gli interventi che riducono i pericoli per chi cammina o va in bicicletta, che richiedono una manutenzione sostenibile e che collegano luoghi importanti, come la scuola, l'ambulatorio e gli uffici pubblici. Se i fondi non basteranno per fare tutto, il Comune inizierà dalle opere più urgenti e più utili alla vita quotidiana.

Quando il progetto sarà approvato, il Comune pubblicherà le date dei lavori e le eventuali modifiche alla circolazione. Durante il cantiere controllerà che le opere siano eseguite bene e in sicurezza. Alla fine pubblicherà una relazione con i risultati, le modifiche apportate e le attività necessarie per mantenere nel tempo gli spazi accessibili, ordinati e sicuri.

Per scegliere le imprese che faranno i lavori, il Comune seguirà le regole previste dalla legge. Controllerà la qualità dei materiali, l'esperienza delle imprese e la loro capacità di rispettare i tempi. Nei documenti di gara saranno indicate anche le misure per proteggere chi passa a piedi, ridurre polvere e rumore e sistemare bene le zone al termine del cantiere. Se nasceranno problemi non previsti, il responsabile del progetto valuterà le possibili soluzioni con i tecnici che seguono i lavori.

Il Comune verificherà anche cosa succede dopo la fine dei lavori. Raccoglierà segnalazioni e informazioni per capire se le nuove opere rendono più semplice e sicuro muoversi ogni giorno. I risultati saranno comunicati ai quartieri e serviranno per scegliere gli interventi futuri. In questo modo i lavori non saranno un'azione isolata: manutenzione, ascolto delle persone e uso attento dei fondi pubblici continueranno a essere collegati.

Le persone potranno trovare sul sito del Comune il calendario aggiornato, le mappe dei percorsi alternativi e i contatti degli uffici. Chi nota un problema potrà inviare una segnalazione, che sarà esaminata dal servizio competente. Il Comune cercherà di rispondere in modo chiaro e di intervenire con priorità quando il problema riguarda la sicurezza o l'accessibilità di un luogo molto frequentato.

Le associazioni e le attività presenti nelle zone interessate potranno partecipare a momenti di confronto anche dopo la conclusione del progetto. I loro suggerimenti aiuteranno a capire se cartelli, rampe, luci e percorsi funzionano nella vita quotidiana. Quando sarà necessario, il Comune potrà programmare piccoli interventi correttivi, così da mantenere nel tempo i risultati ottenuti e da evitare che nuove difficoltà limitino l'uso degli spazi pubblici.
""".strip()

assert len(REFERENCE_TEXT) <= 4000
assert len(SIMPLIFIED_TEXT) <= 4000


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
                "text1": REFERENCE_TEXT,
                "text2": SIMPLIFIED_TEXT,
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
    print(f"Reference text length: {len(REFERENCE_TEXT)} characters")
    print(f"Simplified text length: {len(SIMPLIFIED_TEXT)} characters")
    print()

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
        description="Concurrent Sempl-it text comparison stress test"
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
