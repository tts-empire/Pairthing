# Pairthing — handoff di sviluppo

**Specifica aggiornata:** per onboarding, autenticazione e distribuzione remota prevale il piano in README.md. Il requisito MVP è il primo collegamento via Internet con codice monouso Magic Wormhole. Il Mac mini autorizza il nuovo computer. Prima di ampliare il prodotto eseguire la prova su hotspot descritta nel README.

**Data:** 21 novembre 2026
**Stato:** Specifica iniziale / implementazione MVP
**Nome definitivo:** Pairthing
**Obiettivo:** rendere l'onboarding di nuovi dispositivi Syncthing drasticamente più semplice, mantenendo il motore di sincronizzazione originale e un progetto 100% FOSS.

> **ISTRUZIONE PRINCIPALE A CODEX:** usa questo file come specifica di prodotto e di sviluppo. Leggi prima l'intero handoff. Esamina la directory/repository corrente e gli strumenti disponibili; se il repository è vuoto crea lo scaffold. Non modificare dati o configurazioni Syncthing reali dell'utente senza esplicita approvazione. Implementa in incrementi verificabili, scrivi test, eseguili e documenta risultati e limitazioni. Non fermarti a una proposta teorica: realizza il primo incremento funzionante, nei limiti dell'ambiente.

---

## 0. Contesto e problema da risolvere

Syncthing sincronizza bene i file, ma l'aggiunta di nuovi device è macchinosa: ID lunghi, approvazioni reciproche, aggiunta delle cartelle, configurazioni locali e gestione di più nodi. L'utente vuole un'esperienza comparabile a Dropbox **nell'onboarding**, non un nuovo cloud storage.

**Obiettivo UX:** installare l'app su un nuovo computer, unirlo tramite invito/QR generato su un dispositivo già autorizzato, scegliere cartelle e percorsi locali e avviare la sincronizzazione. L'utente non deve conoscere Device ID, REST API, TLS, Introducer, relay o configurazioni XML/JSON.

**Promessa del prodotto (da dimostrare con test, non da presumere):** “All the power of Syncthing. None of the complexity.”

### Vincoli inderogabili

1. **100% FOSS**: codice sviluppato pubblicamente, dipendenze con licenze compatibili, nessun servizio proprietario obbligatorio, nessun paywall, nessun limite artificiale su utenti/device/cartelle.
2. **Local-first**: nessun account centralizzato richiesto e nessuna archiviazione cloud dei file.
3. **Motore Syncthing upstream non modificato**, finché possibile. Evitare un fork del core Go: facilita sicurezza, manutenzione e aggiornamenti.
4. **Sicurezza prima della comodità**: mai aggiungere device sconosciuti senza autorizzazione valida, mai attivare indiscriminatamente auto-accept, mai esporre REST API amministrativa su Internet.
5. **Compatibilità** con Syncthing esistente: non sovrascrivere configurazioni, chiavi/certificati o database dell'utente.
6. **Installazione semplice**, con obiettivo finale di un unico installer/programma per Windows, macOS e Linux.
7. **Nessuna falsa promessa** di accesso a file quando nessun peer che li possiede è online; Syncthing non è Dropbox con storage centralizzato.

---

## 1. Decisione tecnica iniziale

### Non fare inizialmente un fork di Syncthing

Produrre un **desktop controller + UX proprietaria del progetto (ma codice open source)** che usa un binario ufficiale Syncthing compatibile e la sua REST API in loopback. Il nome del prodotto è Pairthing.

Architettura suggerita:

```
┌──────────────────────────────────────────────────────────┐
│ Pairthing desktop (Tauri 2 + React/TypeScript)             │
│   Setup  |  Dispositivi  |  Cartelle  |  Stato  |  Inviti   │
└───────────────────────┬──────────────────────────────────┘
                        │ Tauri IPC, permessi minimali
┌───────────────────────▼──────────────────────────────────┐
│ Rust controller (trusted local backend)                  │
│ - lifecycle Syncthing / health / REST client             │
│ - inviti + pairing autenticato / scadenze / revoche      │
│ - validazione percorsi / gestione cartelle / transazioni │
│ - gestione segreti e audit non sensibile                 │
└───────────────────────┬──────────────────────────────────┘
                        │ REST (127.0.0.1 + API key privata)
┌───────────────────────▼──────────────────────────────────┐
│ Syncthing upstream (Go; processo esterno / sidecar)      │
│ P2P TLS, discovery, relay, monitoraggio file, versioning  │
└──────────────────────────────────────────────────────────┘
```

**Stack proposto:** Tauri 2, React, TypeScript, Rust, test Rust e test frontend. Se ci sono motivi concreti per scegliere altre tecnologie, documentare la decisione in `docs/ADR/` prima del cambio. Non aggiungere database/server backend remoti per il primo MVP.

### Modalità di integrazione

- **MVP sviluppo**: connettersi a un'istanza Syncthing di TEST già avviata su localhost, oppure avviarne una nuova con home/config/data isolati. Mai assumere che `localhost:8384` sia sempre l'istanza corretta.
- **Distribuzione finale**: includere Syncthing upstream come sidecar per le architetture supportate, con versioni e SHA256 fissati, verifica provenienza/checksum in build e inventario licenze. Gestire l'aggiornamento dell'engine separatamente dall'aggiornamento UI.
- **Istanza esistente**: opzionale modalità “Collega Syncthing esistente”, inizialmente **sola lettura**, con consenso esplicito prima di qualsiasi operazione di scrittura. Non avviare una seconda istanza sullo stesso database/config.
- Le chiamate REST e le credenziali appartengono al backend Rust, **mai al renderer web React**.
- Limitare le capability Tauri e i comandi sidecar: niente `shell` arbitraria richiamabile dal frontend.

**Baseline motore:** puntare alla famiglia **Syncthing 2.x stabile**, rilevare la versione reale a runtime, testare esplicitamente contro una versione 2.x fissata e gestire versioni/API non compatibili con errore esplicito. Non inventare che una particolare versione sia l'ultima: verificarlo quando si implementa il pinning.

---

## 2. UX obbligatoria

### Avvio iniziale

Schermata semplice con due scelte:

- **Crea la mia rete di dispositivi** (primo computer): crea identità locale Syncthing e una cartella di sincronizzazione predefinita scelta dall'utente; spiega brevemente che i dati rimangono sui suoi dispositivi.
- **Collega questo dispositivo**: incolla/apri invito ricevuto da un dispositivo già autorizzato; in futuro QR via fotocamera o app mobile.

### Onboarding principale — da ottimizzare senza sacrificare la sicurezza

1. Sul dispositivo esistente: clic **Aggiungi dispositivo**.
2. Pairthing apre una sessione Magic Wormhole e mostra il codice copiabile, la scadenza e il comando di annullamento.
3. Il nuovo dispositivo inserisce il codice. Il backend negozia il canale PAKE con il Mac mini attraverso un mailbox pubblico e mostra il nome dell’invitante. Il QR è un miglioramento successivo.
4. Il dispositivo invitante conferma l'aggiunta (una sola autorizzazione utente, con nome device). Nessuna approvazione manuale nella GUI Syncthing; il controller configura entrambi i lati.
5. Il nuovo dispositivo sceglie **quali cartelle** ricevere e le **destinazioni locali**; sincronizzazione effettiva dopo autorizzazione. Il dispositivo nuovo non può ricevere cartelle non esplicitamente concesse nell'invito.
6. Schermata finale: online / in attesa / sincronizzazione / errore con testo comprensibile e pulsante per maggiori dettagli tecnici.

**Target UX:** sul device già autorizzato un clic per creare l'invito e una conferma; sul nuovo device apri/incolla invito e scegli percorso/i. Non sono ammessi passaggi con Device ID manuale.

### Dashboard

- Dispositivi: nome, OS (se noto), online/offline, ultimo contatto, sincronizzazione, rimozione autorizzata.
- Cartelle: nome leggibile, percorso locale, dispositivi ammessi, quantità da sincronizzare, eventuali errori/conflitti.
- Inviti: attivi/scaduti/revocati, durata residua, disabilita invito.
- Stato: engine attivo/spento, connessione LAN/Internet, uso relay quando rilevabile, errori traducibili.
- Impostazioni avanzate separate, senza riproporre tutta la GUI nativa di Syncthing nell'MVP.

### Accessibilità

UI in italiano e inglese con stringhe localizzabili, navigazione da tastiera, indicatori non basati soltanto sul colore, feedback chiari. Default percorso dati rispettoso delle convenzioni di ogni sistema operativo.

---

## 3. Pairing e sicurezza: modello concreto

### Distinzione fondamentale

Un Device ID identifica il peer Syncthing. L’autorizzazione iniziale passa da una sessione monouso Magic Wormhole tramite libreria interoperabile, con identificatore applicativo Pairthing comune ai due client. Il Mac mini mantiene la sessione aperta al massimo dieci minuti e la chiude su annullamento, errore di verifica o consumo. Il codice va comunicato attraverso un canale fidato.

Sul canale cifrato scambiare versione applicativa, identità Syncthing, nome leggibile e offerta di cartelle. L’invitato risponde con la propria identità e il sottoinsieme scelto. I percorsi locali rimangono sul dispositivo. Prima delle scritture il proprietario conferma il nuovo peer. Gestire doppia richiesta, interruzione e recupero con stato locale e rilettura della configurazione effettiva.

#### Regole di sicurezza

- Registrare in locale soltanto lo stretto necessario (ID invito, scope, stato, scadenza, nonce consumato); niente segreti in chiaro su log, URL analytics, crash report.
- Per i deep link, evitare perdite accidentali in browser history, referrer e log; preferire handoff alla app con gestione dedicata e documentare i rischi dell'URI scheme.
- Conferma visibile dell'identità e del nome nuovo device dal lato proprietario; il pairing non deve partire in modalità auto-approvazione globale.
- `autoAcceptFolders=false` come default.
- Niente apertura della GUI/REST su `0.0.0.0` e niente API key in JS/UI o parametri pubblici.
- Processi figli con permessi dell'utente, mai `root`/admin per comodità; directory segreti con permessi rigorosi.
- Nuove cartelle ricevute solo con consenso esplicito e percorso validato (no traversal, symlink escape, overwrite fuori root, path collision, cartelle di sistema).
- Aggiornare la configurazione tramite API ufficiali e fare backup transazionale prima di operazioni potenzialmente distruttive.
- Revoca: distinguere **revocare un invito**, **rimuovere un device dalla condivisione** e **rimuovere un device dalla rete**; non eliminare file di dati durante la revoca.

### Introducer Syncthing: utile, ma NON soluzione magica

Secondo la documentazione upstream l'Introducer può propagare la conoscenza dei device per cartella. Però i device manualmente rimossi possono essere **reintrodotti** se restano annunciati dal device che funge da Introducer. Quindi:

1. **V1 (2 device)**: provisioning esplicito e reciproco via REST; nessun Introducer globale necessario.
2. **Fase multi-device**: implementare un modello **owner/introducer fidato**, limitato alle cartelle del gruppo. Gli altri device accettano introduzioni soltanto dall'owner autorizzato per quel gruppo; la specifica di topologia e revoke va testata.
3. **Rimozioni**: prima revocare la membership presso l'owner e nei relativi folder-share, poi propagare e verificare che il device non sia reintrodotto; gestire offline/pending. Se una revoca completa non è dimostrabile, UI deve dichiararlo e non fingere successo.
4. **Owner offline**: dopo la prima presentazione i device già conosciuti possono continuare a sincronizzare direttamente; nuovi ingressi richiedono owner online nella prima implementazione, a meno di una delega sicura progettata successivamente.
5. Evitare configurazioni che introducano tutti i device a tutti i gruppi o condividano automaticamente cartelle private.

**Nota:** controllare la semantica concreta di `introducer`, `skipIntroductionRemovals`, `autoAcceptFolders` nella versione Syncthing scelta. Non generalizzare dalle versioni 1.x.

---

## 4. P2P, discovery e implicazioni reali

- Trasferimenti file effettuati da Syncthing tra dispositivi autorizzati, cifrati; nessun file transitato su un servizio Pairthing centralizzato.
- Funzionamento LAN anche senza account cloud; usare discovery LAN già disponibile nell'engine se appropriato.
- Syncthing può usare servizi pubblici di discovery e relay per connettività Internet; **non dichiarare “nessuna dipendenza esterna”** se sono attivi. Offrire in prospettiva toggle per disabilitarli e istruzioni per alternative self-hosted.
- Relay non equivale a storage: documentare che i file rimangono sincronizzati tra i device e che non esiste una copia centrale sempre disponibile.
- Il primo collegamento via Internet su reti distinte è requisito MVP. Usare Magic Wormhole per il pairing e Syncthing per i trasferimenti.
- Non esporre un listener di pairing pubblico o un server remoto senza autenticazione, rate limiting, timeout e threat model dedicato.

---

## 5. API Syncthing da studiare/integrare

Documentazione upstream da verificare contro il binario scelto:

- API e autenticazione: https://docs.syncthing.net/dev/rest.html
- Config endpoints: https://docs.syncthing.net/rest/config
- `GET /rest/system/status` per `myID` e stato: https://docs.syncthing.net/rest/system-status-get
- `GET/POST/PATCH/PUT` endpoint device e folder **secondo schema reale**: `/rest/config/devices`, `/rest/config/devices/{id}`, `/rest/config/folders`, `/rest/config/folders/{id}`.
- Template di configurazione: `/rest/config/defaults/device` e `/rest/config/defaults/folder`.
- Verifica modifiche pendenti / restart: `/rest/config/restart-required` (verificare supporto e semantica nel target).
- Stati e avanzamento sync: verificare endpoint `/rest/db/status`, `/rest/system/connections`, eventi long polling (`/rest/events`).
- Documentazione Introducer: https://docs.syncthing.net/users/introducer.html
- Config e `autoAcceptFolders`: https://docs.syncthing.net/users/config
- CLI Syncthing 2.x: https://github.com/syncthing/syncthing/blob/main/man/syncthing.1

**Non usare gli endpoint deprecati** `/rest/system/config` per nuova implementazione. Preferire PATCH mirate dove supportate; non fare PUT dell'intera config senza motivazione, perché rischia di sovrascrivere modifiche concorrenti. Dopo ogni modifica rileggere la configurazione e verificare il risultato. Usare adapter versionato con mock per test.

---

## 6. Piano di lavoro incrementale (ordine tassativo)

### M0 — Repo, studio API e sicurezza del laboratorio

**Risultato atteso:** progetto compilabile e testabile senza toccare le configurazioni reali.

- Ispezionare repo e OS; documentare `README.md`, `docs/ARCHITECTURE.md`, `docs/THREAT_MODEL.md`, `docs/ADR/0001-stack.md`.
- Inizializzare Tauri 2 + React TS + Rust, lint/format/test, struttura moduli `syncthing`, `pairing`, `devices`, `folders`, `ui`.
- Implementare adapter Syncthing con `GET /rest/system/status`, lettura config e mapping errori; mock HTTP locale e test unitari.
- Implementare modalità **demo/mock** per sviluppare UI anche senza binario Syncthing; segnalare chiaramente “demo”.
- Implementare modalità test isolata con `--home` / `--config` / `--data` nella directory temporanea dedicata al progetto, con cleanup sicuro. Mai usare la home Syncthing esistente in test automatici.
- Stabilire support matrix per macOS arm64 (Mac mini M4) e Linux x86_64 (Linux Mint) come priorità; Windows in seconda fase.
- Aggiungere un mini tool di diagnostica **read-only**, per verificare release versione/API/collisione porte e permessi.

**Criterio M0:** UI parte su sistema di sviluppo, riconosce engine simulato o isolato e mostra `myID` internamente (non necessariamente nella UI). Nessuna modifica a installazioni reali.

Prima di M1 eseguire la prova di fattibilità su hotspot descritta nel README.

### M1 — Controllo engine e cartelle locali

**Risultato atteso:** su UN computer l'app avvia/ferma un engine isolato e crea una cartella.

- Avvio/stato/stop pulito del processo Syncthing; scelta binario ufficiale installato in dev, sidecar pinning documentato per release.
- Selezione e validazione percorso locale (default esplicito scelto dall'utente); nessuna cartella “Sync” preesistente deve essere sovrascritta.
- Creazione cartella tramite API; stato sync e messaggi di errore leggibili.
- Protezione API key, porta loopback dinamica/controllata, gestione conflitti porta e crash/restart.
- Unit + integration tests con fixture temporanee.

**Criterio M1:** processo gestito senza avvio manuale della GUI Syncthing; creazione di cartella con consenso.

### M2 — Pairing sicuro tra DUE dispositivi (cuore del prodotto)

**Risultato atteso:** un utente collega 2 dispositivi in LAN o su reti Internet diverse senza Device ID manuali.

- Emissione di invito monouso, TTL e pulsante “Annulla invito”.
- Mailbox pubblico e handshake PAKE tramite Magic Wormhole, con connessioni in uscita. Invito copiabile; QR è una visualizzazione aggiuntiva, non un prerequisito.
- Conferma lato proprietario; exchange di identità Syncthing con verifica.
- Provisioning REST reciproco e cartelle **soltanto selezionate**.
- Retry idempotenti: fallimento a metà non deve lasciare condivisioni invisibili / permessi amplificati; definire transazione logica e rollback compensativo.
- Feedback su collegamento, stato di sincronizzazione e cause di errore.
- Test funzionali con due istanze Syncthing isolate su porte/config separate. Test fisici Mac/Linux su LAN e hotspot obbligatori per accettare la milestone.

**Criterio M2:** dopo invito e una conferma, A e B si riconoscono e sincronizzano una cartella test senza operazioni manuali nelle GUI Syncthing.

### M3 — Terzo dispositivo e onboarding ripetibile

- Un device owner gestisce la membership di un gruppo; implementare / validare Introducer **per singolo ambito** e gestione cartelle autorizzate.
- Nuovo C si unisce usando invito di owner A; B apprende C automaticamente senza configurazione manuale.
- Comportamento owner offline, timeout, pairing fallito, riavvio, reti intermittenti.
- Aggiunta/rimozione cartelle, controllo revoca dispositivo e impossibilità di reintroduzione indesiderata.
- Test A-B-C reali/simulati, con owner online/offline e dispositivi non autorizzati.

**Criterio M3:** aggiungere il terzo device non richiede azioni manuali sui device già associati; la revoca non viene annullata dall'Introducer.

### M4 — Installer e distribuzione

- Mac arm64, Linux x86_64 e poi Windows x86_64.
- Binario Syncthing ufficiale per ogni architettura, controlli checksum/provenienza, `NOTICE`, `LICENSES`, SBOM, version pinning.
- Avvio con sistema, tray/minimize-to-tray e background service; UX prevedibile su logout/chiusura app.
- Packaging Tauri documentato, installazione non privilegiata dove possibile, aggiornamenti verificati e rollback.
- CI GitHub Actions con build + test + scansione dipendenze, release firmate ove praticabile.

### M5 — Estensioni successive

Valutare lettura QR, mobile e delega degli inviti dopo il collaudo desktop. Il prodotto deve poter funzionare senza dominio, VPS o servizi gestiti dall’utente.

---

## 7. Test e acceptance criteria non negoziabili

| Test | Risultato atteso |
|---|---|
| Primo avvio | Nessun account, nessun server da gestire, nessun Device ID inserito dall'utente |
| Join con invito valido | Aggiunta reciproca dei due nodi e sole cartelle scelte |
| Invito scaduto, revocato o già usato | Rifiuto senza alterare i device autorizzati |
| Invito contraffatto / MITM / replay | Rifiuto e messaggio privo di segreti |
| Destinazione cartella non valida o collisione | Errore esplicito; nessuna sovrascrittura fuori destinazione |
| Join interrotto a metà | Stato coerente e percorso di recupero/rollback |
| Nuovo dispositivo C | Nessuna approvazione manuale sui device B già autorizzati (M3) |
| Revoca device C | C non può essere reintrodotto dall'owner o da Introducer stale (M3) |
| Owner offline | Sincronizzazione tra peer precedentemente autorizzati prosegue dove connettività e disponibilità file lo consentono |
| Offline totale o assenza di copie disponibili | UI chiarisce che il sync è sospeso, non promette “cloud access” |
| Installazione Syncthing preesistente | Non viene toccata, migrata o sovrascritta senza consenso specifico |
| REST API | Accessibile solo localmente con API key, non dal renderer né da reti esterne |
| Segreti | Non appaiono in log, screenshot di debug, crash report, output CI |
| Licenze | Distribuzione rispettosa di MPL 2.0 e licenze componenti |

Creare test automatizzati con nomi rappresentativi e una sezione `TEST_RESULTS.md` che distingua **eseguiti**, **non eseguiti**, **manuali necessari**, e **bug conosciuti**. Mai indicare un test come passed senza averlo realmente eseguito.

---

## 8. Repository desiderato

Struttura indicativa, modificabile con ADR:

```
pairthing/
├── README.md
├── LICENSE                   # da definire (preferenza MIT per nuovo codice)
├── NOTICE                    # avvisi per Syncthing e dipendenze
├── package.json
├── src/                      # React + TS
│   ├── app/
│   ├── components/
│   ├── pages/
│   ├── i18n/
│   └── services/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── syncthing/
│   │   ├── pairing/
│   │   ├── devices/
│   │   └── folders/
│   ├── capabilities/
│   └── binaries/             # artefatti non committati, costruiti da script
├── scripts/
│   ├── provision-test-engine.*
│   └── verify-upstream-binary.*
├── tests/
│   ├── integration/
│   └── e2e/
└── docs/
    ├── ARCHITECTURE.md
    ├── THREAT_MODEL.md
    ├── API_COMPATIBILITY.md
    ├── TEST_RESULTS.md
    └── ADR/
        └── 0001-stack.md
```

Se il progetto non è già inizializzato, aggiungere `.gitignore`, `.editorconfig`, formatter, test runner, istruzioni di setup riproducibili, file di esempio config **senza segreti**.

---

## 9. Regole operative per Codex

1. **Non chiedere conferme inutili**, procedi quando la decisione è reversibile; per modifiche distruttive, segreti, installazioni di sistema o dati reali serve consenso.
2. Prima di scrivere codice, controlla la versione effettiva di Syncthing e la documentazione/API. Se offline, usa la documentazione disponibile e marca i punti da verificare; non inventare risultati di test.
3. **Niente fork upstream** o patch Syncthing fino a motivazione tecnica forte, test comparativi e ADR.
4. Evita di creare un microservizio cloud o backend aggiuntivo per M0-M2.
5. L'engine esistente dell'utente non è ambiente di test. Non effettuare migrazioni DB, reset o `DELETE` su dati reali.
6. Esponi API locali solo tramite backend protetto. Usa il principio del minimo privilegio per Tauri, filesystem, log e network.
7. Implementa **prima il percorso più stretto funzionante**, poi migliora styling e packaging. Non sostituire il risultato con una documentazione astratta.
8. A ogni milestone: format, lint, test, build; annota esattamente i comandi usati e gli output essenziali.
9. Quando i test richiedono un secondo PC, prepara script/istruzioni manuali copincollabili e dichiara che il test cross-device è ancora da eseguire.
10. Se emergono limiti strutturali di Syncthing Introducer/revoke, **fermati prima di promettere funzioni non sicure** e proponi workaround con rischi chiaramente documentati.
11. Nessuna telemetria obbligatoria. Nessuna comunicazione dei nomi file/folder a un servizio Pairthing.
12. UI semplice; non inserire feature creep (editing Office, calendari, condivisione pubblica di file via web, AI, NAS management).

---

## 10. Prima esecuzione richiesta ADESSO a Codex

Dopo la lettura di questo documento:

**A. Audit dell'ambiente**
- `pwd`, identificazione repo e stato git, OS/architettura, disponibilità Node, Rust, Tauri, Syncthing.
- Se esiste già codice: riusarlo, senza sovrascriverlo.
- Individuare quale API Syncthing 2.x si può effettivamente testare.

**B. Elaborati iniziali**
- `docs/ARCHITECTURE.md` conciso con flusso dati e confini di trust.
- `docs/THREAT_MODEL.md` centrato su invito/pairing, local API, introducer, permessi di cartella.
- `docs/API_COMPATIBILITY.md` con endpoint reali, versioni e prove/curl read-only.
- `README.md` con istruzioni Mac M4/Linux Mint e roadmap.

**C. Codice immediato (M0)**
- Scaffold compilabile Tauri 2 + React/TypeScript + Rust.
- UI con schermate iniziali **Crea rete**, **Collega dispositivo**, **Dispositivi**, **Cartelle**, chiaramente etichettate se non funzionanti.
- `SyncthingClient` Rust con metodi `get_status`, `get_config`, `get_devices`, `get_folders`, gestendo token solo backend e verificando GUI bind loopback.
- Test su mock API per risposta valida, non autenticato, motore assente e versione incompatibile.
- Una demo **read-only** che mostra motore collegato / assente senza modificare configurazioni reali.

**D. Chiusura della prima sessione**
- Riassumere file creati e comandi di build/test effettivamente eseguiti.
- Elencare blocchi reali e cosa manca per M1.
- NON dichiarare implementato il pairing fino al completamento del protocollo sicuro e relativi test.
- NON attendere indicazioni dell'utente per proseguire su operazioni locali non distruttive di M0; se M0 concluso con successo e tempo/tool lo consentono, iniziare M1.

---

## 11. Riferimenti ufficiali

- Syncthing sorgente/licenza: https://github.com/syncthing/syncthing
- Syncthing REST: https://docs.syncthing.net/dev/rest.html
- Config endpoints: https://docs.syncthing.net/rest/config
- Introducer: https://docs.syncthing.net/users/introducer.html
- Parametri di configurazione Syncthing: https://docs.syncthing.net/users/config
- Tauri 2 sidecar: https://v2.tauri.app/develop/sidecar/
- Tauri shell capability: https://v2.tauri.app/plugin/shell/
- MPL 2.0: https://www.mozilla.org/en-US/MPL/2.0/

**Nota legale:** codice Pairthing originale preferibilmente MIT; Syncthing rimane MPL 2.0, con tutti gli obblighi e notice pertinenti alla ridistribuzione. Non chiamare “MIT” l'intero bundle indiscriminatamente. Verificare compatibilità delle dipendenze e traduzioni.

---

## 12. Definizione sintetica di successo

**MVP riuscito:** su due computer (prima Linux/macOS), chi usa Pairthing aggiunge un nuovo dispositivo tramite un invito a scadenza, autorizza in modo verificabile la connessione, seleziona una cartella e ne avvia la sincronizzazione Syncthing **senza aprire la GUI Syncthing né copiare Device ID**. Non esiste account cloud obbligatorio; il prodotto rimane FOSS; sicurezza e dati esistenti non vengono compromessi.

**Traguardo successivo decisivo:** il terzo computer viene associato in modo altrettanto semplice senza richiedere interventi sugli altri nodi, e la revoca di un dispositivo è effettiva anche in presenza di Introducer.

*Fine handoff.*
