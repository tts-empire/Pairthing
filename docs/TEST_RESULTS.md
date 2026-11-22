# Collaudo del 21 novembre 2026

## Eseguito sul Mac mini M4

| Prova | Esito osservato |
| --- | --- |
| `npm test` | Build frontend completata, cinque test Rust superati e un test REST eseguito separatamente contro Syncthing 2.1.6 isolato. |
| `python -m unittest discover -s scripts/pairing` nel venv | Tre test superati per validazione relay, blocco di un profilo parzialmente configurato e protezione delle directory esistenti. |
| `smoke.py` | Due identità isolate, mailbox pubblico e trasferimento TCP su loopback. Codice errato e conferma negata lasciano entrambi i profili privi di peer aggiunti. Quattro contenuti verificati fra invio, ritorno e nuove scritture dopo il riavvio senza codice. |
| `smoke.py --relay-only` | Stessa sequenza con discovery locale disabilitata. Syncthing ha riportato trasporto relay prima e dopo il riavvio. Verificato il contenuto in entrambe le direzioni. |
| `linux_smoke.py` con Docker | Comandi effettivi init, invite, join e sync esercitati fra macOS arm64 con motore 2.1.6 e Linux arm64 in container con motore 2.1.7. Quattro file verificati nelle due direzioni, prima e dopo il riavvio. |

Una prima prova affidata alla sola discovery globale ha superato il tempo limite. Il prototipo scambia anche l’indirizzo del relay già raggiunto dal motore sul canale autenticato e conserva il listener per la ripresa. Nella prova con il filesystem condiviso della VM, le notifiche di scrittura sono risultate insufficienti: per la cartella di prova è prevista una scansione ogni 20 secondi.

## Prova su due computer fisici

Mac mini e portatile Linux hanno completato il pairing con codice e conferma. Il file scritto sul Mac è arrivato sul portatile; la copia creata su Linux è tornata sul Mac con SHA-256 identico. Dopo il riavvio del processo Mac con il comando sync, Syncthing ha ristabilito una connessione TCP diretta classificata come esterna alla LAN.

Il 22 novembre 2026 il Mac ha ricevuto dal portatile la copia di ritorno dopo la ripresa senza un nuovo invito. Il confronto byte per byte e SHA-256 coincide con il file inviato dopo il riavvio. Al controllo il peer era collegato via TCP e la cartella conteneva quattro file, con zero file mancanti e zero errori di ricezione.

## Finestra desktop · 22 novembre 2026

La build Mac arm64 installata è partita con controller e motore inclusi. Nella finestra nativa sono stati azionati **Aggiungi computer** e **Annulla**, verificando il ritorno al modulo di ingresso. Il test `scripts/pairing/desktop_smoke.py` ha esercitato due controller del bundle con profili isolati: generazione e annullamento, nuovo invito, inserimento, conferma, trasferimenti reali in entrambe le direzioni e riapertura di entrambi i processi senza invito. Ripetuto anche con il controller da sorgenti. Verifica della firma locale del bundle superata.

Su Linux ARM64 in container la stessa prova ha verificato trasferimenti bidirezionali e riapertura con due controller avviati dai sorgenti. La build Linux x86_64 su Ubuntu 24.04 ha verificato l’avvio della finestra nativa sotto Xvfb, la creazione del controller incluso tramite IPC e il suo stato iniziale. L’archivio interno `Pairthing-linux-x86_64.tar.gz` scaricato da GitHub ha SHA-256 `d75caa82413f12a96231c3c2f5daa420bc1756ee14252ed39b804b798908fc06`. Resta da provare questa finestra sul Dell fisico. [Esecuzione CI](https://github.com/tts-empire/Pairthing/actions/runs/45014346267)

## Prove aperte

- Linux Mint x86_64, sospensione e cambio di rete durante un trasferimento.
- Ripristino automatico dopo un’interruzione durante il provisioning, revoca di dispositivi e selezione di più cartelle dalla GUI. Il prototipo blocca il riavvio di un profilo con provisioning incompleto.
