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

## Prove aperte

- Linux Mint x86_64, sospensione e cambio di rete durante un trasferimento.
- Ripristino automatico dopo un’interruzione durante il provisioning, revoca di dispositivi e integrazione nelle schermate desktop. Il prototipo blocca il riavvio di un profilo con provisioning incompleto.
