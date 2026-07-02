# Debito pubblico italiano

Dashboard statica per GitHub Pages sull'evoluzione del debito pubblico italiano.

La dashboard include:

- evoluzione mensile del debito delle Amministrazioni pubbliche;
- debito al netto delle disponibilità liquide del Tesoro;
- composizione per strumento;
- vita residua del debito e maturity bucket;
- detentori del debito;
- fabbisogno e variazione mensile del debito;
- tabella con gli ultimi dati disponibili.

## Fonte dati

Fonte principale: Banca d'Italia, *Finanza pubblica: fabbisogno e debito*.

Snapshot incluso:

- pubblicazione: 15 giugno 2026;
- periodo di riferimento: aprile 2026;
- unità originale: milioni di euro.

Il file dati usato dalla dashboard è `data/debt_dashboard.json`.

## Struttura repository

```text
.
├── index.html
├── assets/
│   ├── css/styles.css
│   └── js/app.js
├── data/
│   └── debt_dashboard.json
├── scripts/
│   └── update_data.py
├── .github/workflows/update-data.yml
└── .nojekyll
```

## GitHub Pages

Per pubblicare la dashboard:

1. apri `Settings` del repository;
2. vai su `Pages`;
3. seleziona `Deploy from a branch`;
4. scegli `main` e cartella `/root`;
5. salva.

L'indirizzo sarà normalmente:

```text
https://nazarenolecis.github.io/Debito_pubblico_italiano/
```

## Aggiornamento dati

Lo script `scripts/update_data.py` è predisposto per cercare la pubblicazione mensile della Banca d'Italia e aggiornare il JSON. Il workflow GitHub Actions parte ogni mese e può essere lanciato anche manualmente.

Il parsing automatico di PDF statistici può richiedere correzioni se la struttura della pubblicazione cambia. Per questo il dataset prodotto va verificato prima di usarlo per pubblicazioni o analisi ufficiali.

## Limiti attuali

La prima versione usa il report Banca d'Italia. La scomposizione disponibile è quella per strumenti statistici, vita residua, scadenza originaria, valuta, residenza e detentori. Una scomposizione più granulare per singola tipologia di titolo del Tesoro, come BOT, BTP, CCTeu, BTP Italia, BTP€i, BTP Valore e scadenze per singolo ISIN, richiede una seconda fonte MEF/Dipartimento del Tesoro e può essere aggiunta in un modulo dati separato.
