# Pairthing

Pairthing collega due computer tramite un codice monouso e sincronizza una cartella usando Syncthing. La finestra desktop è disponibile in italiano e inglese.

## Primo collegamento dalla finestra

1. Sul Mac apri **Pairthing** e premi **Aggiungi computer**. Comunica il codice al proprietario dell’altro computer. L’invito dura fino a dieci minuti e si può annullare.
2. Sull’altro computer inserisci il codice nel campo **Codice di collegamento** e premi **Collega**. Entrambe le app devono essere online.
3. Sul Mac verifica il nome del computer e premi **Autorizza**. **Apri cartella** mostra la directory sincronizzata nel gestore file di ciascun computer.
4. Mantieni aperte le app durante i trasferimenti. Dopo averle chiuse, riaprile per riprendere con la stessa identità. La finestra mostra il peer, la disponibilità, il trasporto e gli elementi ancora da trasferire.

Questa build di sviluppo gestisce due dispositivi e una cartella dedicata. La GUI crea il proprio profilo nei dati locali di Pairthing. Chi ha già provato la CLI deve associare le due GUI una volta. Selezione di più cartelle e avvio al login sono in roadmap.

## Aprire le build di sviluppo

- **macOS arm64**. Aprire Pairthing.app. Il bundle preparato con `scripts/build-desktop-mac.sh` include il controller e il motore ed è firmato ad hoc per il collaudo locale.
- **Linux x86_64**. Scaricare l’artefatto del workflow **Desktop Linux**, estrarre lo ZIP, quindi il file `Pairthing-linux-x86_64.tar.gz`. Aprire l’eseguibile **Pairthing** nella cartella estratta e tenere accanto la directory `runtime`. Il pacchetto è compilato su Ubuntu 24.04 e usa le librerie GTK e WebKitGTK 4.1 del sistema. [Build Linux](https://github.com/tts-empire/Pairthing/actions/workflows/desktop-linux.yml)

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

Il mailbox pubblico facilita il primo incontro. La libreria Wormhole autentica il canale con PAKE. Il codice rimane fuori da log e telemetria. Dopo la conferma, il controller Python eseguito dal backend Rust applica le modifiche REST su loopback e custodisce la chiave. La finestra comunica con il controller con comandi IPC limitati. Una sessione interrotta deve poter riprendere o annullare le modifiche parziali. Syncthing gestisce i file tramite collegamenti diretti o relay. Un guasto del mailbox deve lasciare operative le associazioni già completate. [Protocollo Magic Wormhole](https://magic-wormhole.readthedocs.io/en/latest/welcome.html) · [Relay Syncthing](https://docs.syncthing.net/users/relaying.html)

## Sviluppo locale

Servono Node, Rust e i prerequisiti Tauri della piattaforma. Dalla radice eseguire `npm ci`. Con `npm run dev` si apre il frontend demo all’indirizzo indicato da Vite. Per il desktop di sviluppo preparare il runtime descritto nella [guida CLI](scripts/pairing/README.md) e poi eseguire `npm run tauri dev`. Per creare il bundle Mac installare `pyinstaller==6.22.3` nel venv .tools/pair-env ed eseguire `scripts/build-desktop-mac.sh`. Per la suite con un motore locale eseguire `npm test`; su Linux impostare `PAIRTHING_ENGINE` se il binario Syncthing non è nel PATH. Per collegare il desktop al laboratorio temporaneo usare `python3 scripts/lab.py npm run tauri dev`. [Prerequisiti Tauri](https://v2.tauri.app/start/prerequisites/)

L’[handoff di sviluppo](PAIRTHING_CODEX_HANDOFF.md) contiene architettura, vincoli di sicurezza e criteri di collaudo.

## Primo incremento di pairing

È disponibile una [prova funzionante da terminale](scripts/pairing/README.md) con codice Magic Wormhole, conferma del proprietario, provisioning di una cartella e ripresa dopo il riavvio. CLI e finestra desktop usano lo stesso protocollo di associazione. Il primo trasferimento bidirezionale su due computer fisici è documentato nei [risultati del collaudo](docs/TEST_RESULTS.md).
