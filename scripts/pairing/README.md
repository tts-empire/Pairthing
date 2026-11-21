# Prova di collegamento Mac ↔ Linux

Questo incremento collega due motori Syncthing dedicati e condivide una sola cartella di prova chiamata `Files`. Il Mac mini e il computer invitato devono essere accesi durante il primo collegamento. La procedura usa un mailbox pubblico per Magic Wormhole. Syncthing trasferisce i file e conserva le identità per il prossimo avvio. Il prototipo è da terminale.

## Preparazione su entrambi i computer

Occorrono Python 3.12, Syncthing 2.x e il repository Pairthing. Sul Mac viene riconosciuto anche il binario dentro Syncthing.app. Su Linux mettere `syncthing` nel PATH o indicarne il percorso tramite `PAIRTHING_ENGINE`. Dalla radice del repository:

```sh
python3.12 -m venv .tools/pair-env
.tools/pair-env/bin/python -m pip install -r scripts/pairing/requirements.txt
.tools/pair-env/bin/python scripts/pairing/trial.py init "$HOME/Pairthing-prova"
```

Il percorso deve essere nuovo. Il comando crea un profilo privato con configurazione, identità e database propri. Usare soltanto file di prova. L’engine rimane attivo finché il comando invite, join o sync è in esecuzione.

## Associazione su reti diverse

1. Sul Mac mini avviare `.tools/pair-env/bin/python scripts/pairing/trial.py invite "$HOME/Pairthing-prova"`. Comunicare il codice visualizzato al proprietario del portatile tramite un canale fidato.
2. Collegare il portatile Linux all’hotspot del telefono, scollegarlo dalla LAN domestica e avviare `.tools/pair-env/bin/python scripts/pairing/trial.py join "$HOME/Pairthing-prova"`. Inserire il codice quando richiesto. Il terminale nasconde i caratteri durante l’inserimento.
3. Sul Mac mini controllare il nome del computer e confermare con `si`. Su entrambi i computer attendere la comparsa del percorso della cartella.
4. Creare un file in `~/Pairthing-prova/Files`, verificare l’arrivo e confrontare gli hash. Ripetere nella direzione opposta.
5. Fermare entrambi con Ctrl+C. Riavviarli con `.tools/pair-env/bin/python scripts/pairing/trial.py sync "$HOME/Pairthing-prova"`. Verificare un nuovo file in ciascuna direzione. I profili persistono su disco.

L’invito scade dopo dieci minuti. Per annullarlo prima della conferma interrompere il comando. Se la procedura si interrompe durante le scritture di configurazione, chiudere entrambi i processi e ripetere da profili nuovi. Il prototipo conserva i vecchi dati su disco. Il recupero automatico di una transazione interrotta è previsto per M2. La disponibilità del mailbox pubblico è esterna al progetto, e l’idoneità al carico di una distribuzione pubblica resta da verificare.

## Collaudo ripetibile su una macchina

```sh
.tools/pair-env/bin/python scripts/pairing/smoke.py
.tools/pair-env/bin/python scripts/pairing/smoke.py --relay-only
```

Entrambi usano una sessione PAKE reale sul mailbox pubblico, motori indipendenti e profili temporanei. La prima variante limita il trasferimento a loopback. La seconda disattiva la discovery locale e richiede il trasporto via relay. Ogni prova verifica codice errato, conferma negata, contenuti nelle due direzioni e nuovi contenuti dopo il riavvio dei motori. I profili temporanei vengono eliminati al termine.

Per ripetere la prova dei comandi da terminale fra macOS e Linux ARM64 sullo stesso Mac occorre anche Docker con la home utente condivisa in lettura e scrittura. Il container esegue il client con UID non privilegiato, usando un profilo temporaneo distinto da quello del Mac.

```sh
docker build -f scripts/pairing/Dockerfile.test -t pairthing-trial:local scripts/pairing
.tools/pair-env/bin/python scripts/pairing/linux_smoke.py
.tools/pair-env/bin/python -m unittest discover -s scripts/pairing -p 'test_*.py'
```
