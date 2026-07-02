# Debito pubblico italiano

Repository per scaricare, normalizzare e validare dati ufficiali sul debito pubblico italiano.

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
- tipologie dei titoli di Stato pubblicati dal Tesoro;
- ISIN, emissioni, aste, scadenze, rimborsi, cedole, tassi e rendimenti quando presenti nei file ufficiali del Tesoro;
- tassi benchmark sui titoli pubblici italiani a lungo termine da Eurostat.

## Fonti ufficiali

La pipeline usa tre blocchi di fonti.

1. Banca d'Italia, Base Dati Statistica, pubblicazione FPI, `Finanza pubblica: fabbisogno e debito`.

Questa fonte copre debito delle Amministrazioni pubbliche, fabbisogno, strumenti, vita residua, scadenza originaria, valuta, residenza dei creditori, detentori e attività liquide.

2. MEF, Dipartimento del Tesoro, area debito pubblico e titoli di Stato.

Questa fonte viene usata per i dettagli granulari sui titoli del Tesoro, inclusi BOT, BTP, CCTeu, BTP Italia, BTP€i, BTP Valore, ISIN, aste, emissioni, scadenze, rimborsi, cedole, tassi e rendimenti quando presenti nei file ufficiali pubblicati dal Tesoro.

3. Eurostat, dataset `irt_lt_mcby_m`.

Questa fonte viene usata per la serie mensile ufficiale dei rendimenti a lungo termine sui titoli di Stato italiani.

Il file `sources_manifest.csv` documenta le fonti ufficiali di partenza e può essere esteso con URL specifici del Tesoro quando vengono individuati file stabili per aste, scadenze, rimborsi e stock per ISIN.

## Struttura

```text
.
├── requirements.txt
├── sources_manifest.csv
├── .github/workflows/update-data.yml
├── scripts/
│   ├── config.py
│   ├── io_utils.py
│   ├── normalization_utils.py
│   ├── bankitalia_fpi.py
│   ├── mef_discovery.py
│   ├── mef_treasury.py
│   ├── eurostat_rates.py
│   ├── normalize_bankitalia.py
│   ├── normalize_mef.py
│   ├── quality_checks.py
│   └── build_all_datasets.py
└── tests/
    └── test_normalization_utils.py
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

## Test

```bash
python -m pytest
```

I test coprono le utility di parsing per numeri italiani, date, ISIN e classificazione di base delle tipologie di titolo.

## Esecuzione completa

```bash
python scripts/build_all_datasets.py
```

La pipeline genera output sotto:

```text
data/processed/
```

La sequenza è:

1. download e conversione source-level da Banca d'Italia, MEF/Tesoro ed Eurostat;
2. costruzione dei dataset finali standardizzati;
3. controlli qualità;
4. scrittura di `data/processed/pipeline_run_metadata.json`.

## Aggiornamento automatico

Il workflow GitHub Actions è in:

```text
.github/workflows/update-data.yml
```

Parte automaticamente il giorno 1 di ogni mese alle 04:00 UTC e può essere lanciato manualmente da `Actions -> Update public debt data -> Run workflow`.

Il workflow:

- installa le dipendenze Python;
- esegue `python -m pytest`;
- esegue `python scripts/build_all_datasets.py`;
- carica come artifact il report qualità;
- aggiunge al commit solo `data/processed/`;
- crea un commit solo se i CSV generati sono cambiati.

Il workflow usa `concurrency` per evitare sovrapposizioni tra aggiornamenti mensili e run manuali.

## Output Banca d'Italia source-level

```text
data/processed/bankitalia/fpi_all_data.csv
data/processed/bankitalia/fpi_core_tables.csv
data/processed/bankitalia/fpi_all_metadata.csv
data/processed/bankitalia/fpi_catalog.csv
data/processed/bankitalia/tables/*.csv
data/processed/bankitalia/metadata/*.csv
```

`fpi_all_data.csv` concatena tutte le tavole dati della pubblicazione FPI mantenendo tutte le colonne originali. `fpi_core_tables.csv` filtra le tavole principali utili per debito, strumenti, detentori, vita residua, scadenza originaria, valuta e residenza.

## Output MEF / Tesoro source-level

```text
data/processed/mef/mef_pages.csv
data/processed/mef/mef_links.csv
data/processed/mef/mef_download_catalog.csv
data/processed/mef/mef_all_tables_wide.csv
data/processed/mef/mef_all_cells_long.csv
data/processed/mef/files/*.csv
```

`mef_all_tables_wide.csv` conserva le tabelle in formato vicino all'originale. `mef_all_cells_long.csv` conserva ogni cella con numero di riga, numero di colonna, URL fonte, pagina fonte, file locale e foglio Excel. Questo formato serve per non perdere dettagli quando i file del Tesoro hanno intestazioni multiple, note o layout non standard.

## Output Eurostat source-level

```text
data/processed/eurostat/italy_long_term_government_bond_yield.csv
data/processed/eurostat/eurostat_rates_metadata.json
```

## Dataset finali

```text
data/processed/final/debt_total_monthly.csv
data/processed/final/debt_by_instrument.csv
data/processed/final/debt_by_holder.csv
data/processed/final/debt_by_subsector.csv
data/processed/final/debt_deposits_and_liquid_assets.csv
data/processed/final/debt_by_residual_maturity.csv
data/processed/final/debt_by_original_maturity_currency_residency.csv
data/processed/final/central_government_debt_by_original_maturity_currency_residency.csv
data/processed/final/public_sector_borrowing_requirement_by_instrument.csv
data/processed/final/treasury_securities_by_isin.csv
data/processed/final/treasury_auctions.csv
data/processed/final/treasury_redemptions.csv
data/processed/final/interest_rates.csv
```

I dataset finali mantengono le colonne originali e aggiungono campi standard quando riconosciuti, per esempio `date`, `value_mln_eur`, `standard_table_code`, `standard_table_name`, `isin`, `security_type`, `candidate_date_1`, `candidate_numeric_value`, `rate_source` e `rate_type`.

## Controlli qualità

```text
data/processed/quality/validation_report.csv
data/processed/quality/validation_summary.json
```

I controlli distinguono tra errori critici e warning. Gli errori critici bloccano il workflow. I warning vengono salvati nel report e servono per capire quali dataset finali richiedono ispezione manuale.

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
- dataset Eurostat;
- path del manifest delle fonti.

## Principio metodologico

La pipeline privilegia la conservazione del dato grezzo ufficiale. Per questo:

- non elimina colonne originali;
- non forza tutte le fonti in uno schema unico;
- aggiunge colonne di provenienza a ogni output;
- salva cataloghi delle fonti scaricate;
- produce sia formato wide sia formato cella-per-riga per i file del Tesoro;
- costruisce uno strato finale standardizzato sopra i CSV source-level;
- salva report qualità per ogni run.

Il parser MEF resta la parte da verificare con più attenzione dopo il primo run, perché il Tesoro può pubblicare file con layout diversi. Il formato cella-per-riga consente di recuperare le informazioni anche quando il parser finale richiede affinamenti.
