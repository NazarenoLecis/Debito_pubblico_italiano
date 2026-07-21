# Debito pubblico italiano

Repository per scaricare, normalizzare, validare e pubblicare dati ufficiali sul debito pubblico italiano.

Questo repository produce dati. La parte visuale vive nei repository dedicati al sito.

## Obiettivo

Produrre output aggiornabili in CSV e JSON su:

- evoluzione del debito pubblico nel tempo;
- fabbisogno delle Amministrazioni pubbliche;
- composizione del debito per strumenti;
- vita residua e scadenza originaria;
- profilo scadenze dei titoli per anno e trimestre;
- valuta e residenza dei creditori;
- settori detentori del debito;
- depositi e disponibilita liquide del Tesoro;
- tipologie dei titoli di Stato pubblicati dal Tesoro;
- ISIN, emissioni, aste, scadenze, rimborsi, cedole, tassi e rendimenti quando presenti nei file ufficiali del Tesoro;
- rendimenti lordi all'emissione di BOT e BTP per scadenza da Banca d'Italia;
- rendimento di riferimento a lungo termine sui titoli pubblici italiani da Eurostat;
- costo del debito pubblico, in valori nominali e in percentuale del PIL, da Eurostat;
- payload pubblico compatto per riuso web.

## Fonti ufficiali

La pipeline usa quattro blocchi di fonti.

1. Banca d'Italia, Base Dati Statistica, pubblicazione FPI, `Finanza pubblica: fabbisogno e debito`.

Questa fonte copre debito delle Amministrazioni pubbliche, fabbisogno, strumenti, vita residua, scadenza originaria, valuta, residenza dei creditori, detentori e attivita liquide.

2. MEF, Dipartimento del Tesoro, area debito pubblico e titoli di Stato.

Questa fonte viene usata per i dettagli granulari sui titoli del Tesoro, inclusi BOT, BTP, CCTeu, BTP Italia, BTP euro indicizzati, BTP Valore, ISIN, aste, emissioni, scadenze, rimborsi, cedole, tassi e rendimenti quando presenti nei file ufficiali pubblicati dal Tesoro.

3. Banca d'Italia, Base Dati Statistica, cubo `RTIT0100`.

Questa fonte viene usata per i rendimenti lordi mensili all'emissione dei titoli di Stato, inclusi BOT 12 mesi e BTP a 5, 10 e 20 anni.

4. Eurostat, dataset `irt_lt_mcby_m` e `gov_10a_main`.

Questa fonte viene usata per la serie mensile ufficiale del rendimento di riferimento a lungo termine sui titoli di Stato italiani e per la voce annuale `D41PAY`, interessi passivi delle Amministrazioni pubbliche, in milioni di euro e in percentuale del PIL.

Il file `sources_manifest.csv` documenta le fonti ufficiali di partenza.

## Struttura

```text
.
|-- requirements.txt
|-- sources_manifest.csv
|-- .github/workflows/update-data.yml
|-- scripts/
|   |-- config.py
|   |-- io_utils.py
|   |-- normalization_utils.py
|   |-- bankitalia_fpi.py
|   |-- bankitalia_market_rates.py
|   |-- mef_discovery.py
|   |-- mef_treasury.py
|   |-- eurostat_rates.py
|   |-- normalize_bankitalia.py
|   |-- normalize_mef.py
|   |-- normalize_eurostat.py
|   |-- build_public_payload.py
|   |-- quality_checks.py
|   `-- build_all_datasets.py
|-- notebooks/
|   |-- 01_quadro_generale.ipynb
|   |-- 02_profilo_scadenze.ipynb
|   `-- 03_costo_e_rendimenti.ipynb
`-- tests/
    `-- test_normalization_utils.py
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

## Notebook di analisi

I notebook in `notebooks/` sono pensati per analisi esplorativa e riproduzione dei grafici principali. Leggono il file:

```text
output/data/public/debito-pubblico.json
```

Per aggiornarli con i dati piu recenti:

```bash
python scripts/build_all_datasets.py
```

Poi apri i notebook:

```text
notebooks/01_quadro_generale.ipynb
notebooks/02_profilo_scadenze.ipynb
notebooks/03_costo_e_rendimenti.ipynb
```

Ogni figura include in basso a sinistra fonte ed elaborazione.

## Esecuzione completa

```bash
python scripts/build_all_datasets.py
```

La pipeline genera output sotto:

```text
output/data/
```

La sequenza e:

1. download e conversione source-level da Banca d'Italia, MEF/Tesoro ed Eurostat;
2. costruzione dei dataset finali standardizzati;
3. scrittura dei file JSON accanto ai CSV finali;
4. costruzione del payload pubblico `output/data/public/debito-pubblico.json`;
5. controlli qualita;
6. scrittura di `output/data/pipeline_run_metadata.json`.

## Output Banca d'Italia source-level

```text
output/data/bankitalia/fpi_all_data.csv
output/data/bankitalia/fpi_all_data.json
output/data/bankitalia/fpi_core_tables.csv
output/data/bankitalia/fpi_core_tables.json
output/data/bankitalia/fpi_all_metadata.csv
output/data/bankitalia/fpi_all_metadata.json
output/data/bankitalia/fpi_catalog.csv
output/data/bankitalia/fpi_catalog.json
output/data/bankitalia/tables/*.csv
output/data/bankitalia/tables/*.json
output/data/bankitalia/metadata/*.csv
output/data/bankitalia/metadata/*.json
```

`fpi_all_data.csv` concatena tutte le tavole dati della pubblicazione FPI mantenendo tutte le colonne originali. `fpi_core_tables.csv` filtra le tavole principali utili per debito, strumenti, detentori, vita residua, scadenza originaria, valuta e residenza.

## Output MEF / Tesoro source-level

```text
output/data/mef/mef_pages.csv
output/data/mef/mef_pages.json
output/data/mef/mef_links.csv
output/data/mef/mef_links.json
output/data/mef/mef_download_catalog.csv
output/data/mef/mef_download_catalog.json
output/data/mef/mef_all_tables_wide.csv
output/data/mef/mef_all_tables_wide.json
output/data/mef/mef_all_cells_long.csv
output/data/mef/mef_all_cells_long.json
output/data/mef/files/*.csv
output/data/mef/files/*.json
```

`mef_all_tables_wide.csv` conserva le tabelle in formato vicino all'originale. `mef_all_cells_long.csv` conserva ogni cella con numero di riga, numero di colonna, URL fonte, pagina fonte, file locale e foglio Excel. Questo formato serve per non perdere dettagli quando i file del Tesoro hanno intestazioni multiple, note o layout non standard.

## Output Eurostat source-level

```text
output/data/eurostat/italy_long_term_government_bond_yield.csv
output/data/eurostat/italy_long_term_government_bond_yield.json
output/data/eurostat/italy_public_debt_interest_cost.csv
output/data/eurostat/italy_public_debt_interest_cost.json
output/data/eurostat/eurostat_rates_metadata.json
output/data/eurostat/eurostat_debt_cost_metadata.json
```

## Dataset finali

```text
output/data/final/debt_total_monthly.csv
output/data/final/debt_total_monthly.json
output/data/final/debt_by_instrument.csv
output/data/final/debt_by_instrument.json
output/data/final/debt_by_holder.csv
output/data/final/debt_by_holder.json
output/data/final/debt_by_subsector.csv
output/data/final/debt_by_subsector.json
output/data/final/debt_deposits_and_liquid_assets.csv
output/data/final/debt_deposits_and_liquid_assets.json
output/data/final/debt_by_residual_maturity.csv
output/data/final/debt_by_residual_maturity.json
output/data/final/debt_by_original_maturity_currency_residency.csv
output/data/final/debt_by_original_maturity_currency_residency.json
output/data/final/central_government_debt_by_original_maturity_currency_residency.csv
output/data/final/central_government_debt_by_original_maturity_currency_residency.json
output/data/final/public_sector_borrowing_requirement_by_instrument.csv
output/data/final/public_sector_borrowing_requirement_by_instrument.json
output/data/final/debt_fiscal_indicators.csv
output/data/final/debt_fiscal_indicators.json
output/data/final/treasury_securities_by_isin.csv
output/data/final/treasury_securities_by_isin.json
output/data/final/treasury_auctions.csv
output/data/final/treasury_auctions.json
output/data/final/treasury_redemptions.csv
output/data/final/treasury_redemptions.json
output/data/final/treasury_maturity_profile.csv
output/data/final/treasury_maturity_profile.json
output/data/final/interest_rates.csv
output/data/final/interest_rates.json
output/data/final/debt_interest_cost.csv
output/data/final/debt_interest_cost.json
output/data/final/security_issuance_yields.csv
output/data/final/security_issuance_yields.json
```

I dataset finali mantengono le colonne originali e aggiungono campi standard quando riconosciuti, per esempio `date`, `value_mln_eur`, `standard_table_code`, `standard_table_name`, `isin`, `security_type`, `candidate_date_1`, `candidate_numeric_value`, `rate_source` e `rate_type`.

## Payload pubblico

```text
output/data/public/debito-pubblico.json
```

Il payload pubblico contiene KPI, serie storiche principali, sezioni tematiche, note metodologiche e fonti in una struttura compatta pensata per essere pubblicata come:

```text
https://data.nazarenolecis.com/debito-pubblico/data.json
```

La pubblicazione su R2 viene gestita dal repository `nazarenolecis-data-pipeline`.

## Controlli qualita

```text
output/data/quality/validation_report.csv
output/data/quality/validation_report.json
output/data/quality/validation_summary.json
```

I controlli distinguono tra errori critici e warning. Gli errori critici bloccano il workflow. I warning vengono salvati nel report e servono per capire quali dataset finali richiedono ispezione manuale.

## Aggiornamento automatico

Il workflow GitHub Actions e in:

```text
.github/workflows/update-data.yml
```

Parte automaticamente il giorno 16 di ogni mese alle 04:30 UTC e puo essere lanciato manualmente da `Actions -> Update public debt data -> Run workflow`.

Il workflow:

- installa le dipendenze Python;
- esegue `python -m pytest`;
- esegue `python scripts/build_all_datasets.py`;
- carica come artifact il report qualita;
- carica come artifact il payload pubblico;
- lascia la pubblicazione mensile su R2 al repository `nazarenolecis-data-pipeline`.

Il workflow usa `concurrency` per evitare sovrapposizioni tra aggiornamenti mensili e run manuali.

## Configurazione

Le impostazioni sono in:

```text
scripts/config.py
```

Da li si modificano:

- cartelle di output;
- URL iniziali del Tesoro;
- parole chiave per trovare file rilevanti;
- esclusioni per file non tabellari del MEF;
- profondita massima di esplorazione delle pagine MEF;
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
- salva file JSON per il riuso applicativo;
- salva report qualita per ogni run.

Il parser MEF resta la parte da verificare con piu attenzione dopo ogni evoluzione delle pagine del Tesoro, perche i file ufficiali possono avere layout diversi. Il formato cella-per-riga consente di recuperare le informazioni anche quando il parser finale richiede affinamenti.
