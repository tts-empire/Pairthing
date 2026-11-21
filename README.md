# Pairthing

Pairthing è un controller desktop FOSS per sincronizzare cartelle fra Mac e Linux con Syncthing. Il primo incremento contiene un’interfaccia Tauri bilingue, una demo locale e un adapter Rust in sola lettura per un motore di laboratorio. Il pairing è disponibile come prova da terminale. La sua integrazione nel desktop è pianificata.

## Primo collegamento

1. Sul Mac mini M4 scegli **Aggiungi computer**, seleziona le cartelle da offrire e comunica il codice temporaneo al nuovo computer tramite un canale fidato.
2. Sul nuovo Mac o PC Linux scegli **Collega dispositivo**, inserisci il codice e scegli le cartelle e i percorsi locali. Entrambe le app devono essere online durante l’associazione.
3. Il Mac mini mostra il dispositivo in arrivo per la conferma. Pairthing configura i due motori. Ai successivi avvii Syncthing riprende automaticamente quando un peer con una copia è online.

Il primo collegamento deve funzionare anche da reti Internet diverse, senza acquistare un dominio, gestire un VPS, aprire porte o creare un account. Per autorizzare un computer quando sei fuori casa devi poter ottenere un invito attivo dal Mac mini.

## Piano di sviluppo

| Tappa | Consegna | Prova per procedere |
| --- | --- | --- |
| M0 · Laboratorio | Demo Tauri e adapter Rust, motori e dati temporanei separati dall’installazione personale. | Build desktop, test adapter e letture su un motore isolato. |
| Prova di fattibilità · prima di investire nel prodotto | Due piccoli client usano una libreria Magic Wormhole interoperabile, lo stesso identificatore applicativo e un mailbox pubblico. Verificare condizioni d’uso e disponibilità del mailbox per applicazioni di terzi. Scambiare i Device ID sul canale autenticato e configurare due motori isolati. | Mac mini su rete domestica e portatile Linux su hotspot, senza VPN o port forwarding. Inserire un solo codice, scambiare un file in entrambe le direzioni e confrontare gli hash. Ripetere dopo il riavvio senza codice. Registrare rete e trasporto effettivi. Se la prova non passa, sospendere packaging e sviluppo multi-device e documentare il blocco. |
| M1 · Motore e cartelle | Gestire avvio e arresto, identità persistente, selezione della destinazione e stato trasferimenti. | Riapertura senza perdita dell’identità, gestione porta occupata e protezione delle cartelle preesistenti. |
| M2 · Onboarding desktop | Integrare la prova nelle UI italiane e inglesi. Codice monouso con scadenza di 10 minuti e annullamento, conferma del proprietario, permessi limitati alle cartelle offerte e selezionate. | Completare il percorso su LAN e su hotspot. Verificare codice errato, scaduto, annullato o riutilizzato, mailbox irraggiungibile, disconnessione durante il provisioning e trasferimento tramite relay. |
| M3 · Più computer | Il master autorizza nuovi ingressi, gestisce membership e revoca per cartella. | Il terzo computer entra con un invito. I peer offline recuperano le revoche prima di dichiarare la rimozione completa. |
| M4 · Distribuzione | Installer macOS arm64 e Linux x86_64 con engine upstream verificato, licenze e avvio automatico. | Installazione pulita, aggiornamento e ripristino verificati su entrambe le piattaforme. |

Il mailbox pubblico facilita il primo incontro. La libreria Wormhole autentica il canale con PAKE. Il codice rimane fuori da log e telemetria. Dopo la conferma, il backend Rust applica modifiche REST mirate su loopback; l’API key rimane nel backend. Una sessione interrotta deve poter riprendere o annullare le modifiche parziali. Syncthing gestisce i file tramite collegamenti diretti o relay. Un guasto del mailbox deve lasciare operative le associazioni già completate. [Protocollo Magic Wormhole](https://magic-wormhole.readthedocs.io/en/latest/welcome.html) · [Relay Syncthing](https://docs.syncthing.net/users/relaying.html)

## Sviluppo locale

Servono Node, Rust e i prerequisiti Tauri della piattaforma. Dalla radice eseguire `npm ci`. Con `npm run dev` si apre il frontend demo all’indirizzo indicato da Vite. Per il desktop eseguire `npm run tauri dev`. Per la suite con un motore locale eseguire `npm test`; su Linux impostare `PAIRTHING_ENGINE` se il binario Syncthing non è nel PATH. Per collegare il desktop al laboratorio temporaneo usare `python3 scripts/lab.py npm run tauri dev`. [Prerequisiti Tauri](https://v2.tauri.app/start/prerequisites/)

L’[handoff di sviluppo](PAIRTHING_CODEX_HANDOFF.md) contiene architettura, vincoli di sicurezza e criteri di collaudo.

## Primo incremento di pairing

È disponibile una [prova funzionante da terminale](scripts/pairing/README.md) con codice Magic Wormhole, conferma del proprietario, provisioning di una cartella e ripresa dopo il riavvio. La dashboard Tauri rimane in sola lettura. Il collaudo fisico Mac/Linux via hotspot è ancora da eseguire.
