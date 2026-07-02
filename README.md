# Debito pubblico italiano

Repository per scaricare e normalizzare dati ufficiali sul debito pubblico italiano.

Il repository non contiene una dashboard. Contiene codice Python per generare dataset CSV da fonti ufficiali.

## Obiettivo

Produrre file CSV aggiornabili su:

- evoluzione del debito pubblico nel tempo;
- fabbisogno delle Amministrazioni pubbliche;
- composizione del debito per strumenti;
- vita residua e scadenza originaria;
- valuta e residenza dei creditori;
- settori detentori del debito;
- depositi e disponibilità liquide del Tesoro;
- tipologie dei titoli di Stato, dove disponibili nei file del Tesoro;
- ISIN, emissioni, aste, scadenze, rimborsi, cedole, tassi e rendimenti, dove disponibili nei file del Tesoro;
- tassi benchmark sui titoli pubblici italiani a lungo termine da Eurostat.

## Fonti ufficiali

La pipeline usa tre blocchi di fonti.

1. Banca d'Italia, Base Dati Statistica, pubblicazione FPI, `Finanza pubblica: fabbisogno e debito`.

Questa fonte copre debito delle Amministrazioni pubbliche, fabbisogno, strumenti, vita residua, scadenza originaria, valuta, residenza dei creditori, detentori e attività liquide.

2. MEF, Dipartimento del Tesoro, area debito pubblico e titoli di Stato.

Questa fonte viene usata per i dettagli granulari sui titoli del Tesoro, inclusi BOT, BTP, CCTeu, BTP Italia, BTP€i, BTP Valore, ISIN, aste, emissioni, scadenze, rimborsi, cedole, tassi e rendimenti quando presenti nei file ufficiali pubblicati dal Tesoro.

3. Eurostat, dataset `irt_lt_mcby_m`.

Questa fonte viene usata per la serie mensile ufficiale dei rendimenti a lungo termine sui titoli di Stato italiani.

## Struttura

```text
.
├── requirements.txt
└── scripts/
    ├── config.py
    ├── io_utils.py
    ├── bankitalia_fpi.py
    ├── mef_discovery.py
    ├── mef_treasury.py
    ├── eurostat_rates.py
    └── build_all_datasets.py
```

## Installazione

Da terminale, nella cartella del repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Su Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Esecuzione completa

```bash
python scripts/build_all_datasets.py
```

La pipeline genera output sotto:

```text
data/processed/
```

## Output Banca d'Italia

```text
data/processed/bankitalia/fpi_all_data.csv
data/processed/bankitalia/fpi_core_tables.csv
data/processed/bankitalia/fpi_all_metadata.csv
data/processed/bankitalia/fpi_catalog.csv
data/processed/bankitalia/tables/*.csv
data/processed/bankitalia/metadata/*.csv
```

`fpi_all_data.csv` concatena tutte le tavole dati della pubblicazione FPI mantenendo tutte le colonne originali. `fpi_core_tables.csv` filtra le tavole principali utili per debito, strumenti, detentori, vita residua, scadenza originaria, valuta e residenza.

## Output MEF / Tesoro

```text
data/processed/mef/mef_pages.csv
data/processed/mef/mef_links.csv
data/processed/mef/mef_download_catalog.csv
data/processed/mef/mef_all_tables_wide.csv
data/processed/mef/mef_all_cells_long.csv
data/processed/mef/files/*.csv
```

`mef_all_tables_wide.csv` conserva le tabelle in formato vicino all'originale. `mef_all_cells_long.csv` conserva ogni cella con numero di riga, numero di colonna, URL fonte, pagina fonte, file locale e foglio Excel. Questo formato serve per non perdere dettagli quando i file del Tesoro hanno intestazioni multiple, note o layout non standard.

## Output Eurostat

```text
data/processed/eurostat/italy_long_term_government_bond_yield.csv
data/processed/eurostat/eurostat_rates_metadata.json
```

## Configurazione

Le impostazioni sono in:

```text
scripts/config.py
```

Da lì si modificano:

- cartelle di output;
- URL iniziali del Tesoro;
- parole chiave per trovare file rilevanti;
- profondità massima di esplorazione delle pagine MEF;
- opzioni Banca d'Italia BDS;
- dataset Eurostat.

## Principio metodologico

La pipeline privilegia la conservazione del dato grezzo ufficiale. Per questo:

- non elimina colonne originali;
- non forza tutte le fonti in uno schema unico;
- aggiunge colonne di provenienza a ogni output;
- salva cataloghi delle fonti scaricate;
- produce sia formato wide sia formato cella-per-riga per i file del Tesoro.

Un dataset analitico finale con variabili standardizzate, per esempio `date`, `isin`, `security_type`, `auction_yield`, `coupon`, `issue_amount`, `outstanding_amount`, `maturity_date`, può essere costruito sopra questi CSV dopo aver verificato i layout effettivi dei file MEF scaricati.
