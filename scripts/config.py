"""Configuration for the Italian public debt data pipeline.

The project uses one Python configuration file instead of YAML or argparse.
Change the variables in this file when sources, folders or pipeline behaviour
need to be updated.
"""

from pathlib import Path


# Root folders. The repository keeps generated outputs under output/.
# output/data contains datasets, raw downloads, metadata and quality reports.
# output/charts is reserved for future figures built from the final datasets.
OUTPUT_DIR = Path("output")
DATA_DIR = OUTPUT_DIR / "data"
CHARTS_DIR = OUTPUT_DIR / "charts"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR
FINAL_DIR = DATA_DIR / "final"
QUALITY_DIR = DATA_DIR / "quality"
SOURCE_MANIFEST_FILE = Path("sources_manifest.csv")


# General behaviour.
# KEEP_RAW_FILES=True stores the original official downloads.
# CLEAN_OUTPUT=True rebuilds source-level output folders from scratch.
KEEP_RAW_FILES = True
CLEAN_OUTPUT = True
REQUEST_TIMEOUT_SECONDS = 180


# Banca d'Italia BDS A2A source.
# FPI is the BDS publication for "Finanza pubblica: fabbisogno e debito".
# The ALL export returns data, domains, legends and structure files in one ZIP.
BANKITALIA_A2A_BASE_URL = "https://a2a.bancaditalia.it/infostat/dataservices/export"
BANKITALIA_COMMUNITY = "BANKITALIA"
BANKITALIA_CONTEXT = "DIFF"
BANKITALIA_LOCALE = "IT"
BANKITALIA_FORMAT = "CSV"
BANKITALIA_CONTENT_TYPE = "ALL"
BANKITALIA_OBJECT_TYPE = "PUBLICATION"
BANKITALIA_PUBLICATION_CODE = "FPI"
BANKITALIA_PUBLICATION_NAME = "Finanza pubblica: fabbisogno e debito"


# These table codes are the main public-finance tables used for debt analysis.
# The script does not discard other tables. These labels are used to make the
# generated catalogue readable.
BANKITALIA_CORE_TABLES = {
    "TCCE0100": "Formazione del fabbisogno delle Amministrazioni centrali",
    "TCCE0125": "Finanziamento del fabbisogno delle Amministrazioni pubbliche per strumenti",
    "TCCE0155": "Finanziamento del fabbisogno delle Amministrazioni pubbliche per sottosettori",
    "TCCE0175": "Debito delle Amministrazioni pubbliche per strumenti",
    "TCCE0200": "Debito delle Amministrazioni pubbliche per settori detentori",
    "TCCE0225": "Debito delle Amministrazioni pubbliche per sottosettori",
    "TCCE0250": "Debito delle Amministrazioni locali per comparti e strumenti",
    "TCCE0275": "Debito delle Amministrazioni locali per aree geografiche",
    "TCCE0300": "Debito, depositi e altre attività delle Amministrazioni pubbliche",
    "TCCE0325": "Debito delle Amministrazioni pubbliche per vita residua",
    "TCCE0350": "Debito delle Amministrazioni pubbliche per scadenza originaria, strumento, valuta e residenza dei creditori",
    "TCCE0375": "Debito delle Amministrazioni centrali per scadenza originaria, strumento, valuta e residenza dei creditori",
    "TCCE0400": "Indebitamento netto e debito delle Amministrazioni pubbliche in percentuale del PIL",
}


# MEF / Dipartimento del Tesoro source.
# The crawler starts from the manifest when available and falls back to these
# URLs. It follows internal links that contain public-debt keywords and
# downloads tabular files.
MEF_START_URLS = [
    "https://www.dt.mef.gov.it/it/debito_pubblico/",
    "https://www.dt.mef.gov.it/it/debito_pubblico/dati_statistici/",
    "https://www.dt.mef.gov.it/it/debito_pubblico/titoli_di_stato/",
]
MEF_ALLOWED_DOMAIN = "www.dt.mef.gov.it"
MEF_MAX_CRAWL_PAGES = 250
MEF_MAX_DEPTH = 4
MEF_LINK_KEYWORDS = [
    "debito",
    "titoli",
    "stato",
    "bot",
    "btp",
    "cct",
    "ctz",
    "asta",
    "aste",
    "emissioni",
    "scadenze",
    "rimborsi",
    "vita-media",
    "tassi",
    "rendimenti",
    "statistici",
]
MEF_FILE_EXTENSIONS = [".csv", ".xlsx", ".xls", ".zip"]
MEF_EXCLUDED_FILE_KEYWORDS = [
    "video",
    "avi",
    "mp4",
    "multimedia",
]


# Eurostat source for benchmark long-term government bond yields.
# This is useful as a clean official interest-rate time series. Auction yields
# and coupon-level information are downloaded from MEF files when available.
EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
EUROSTAT_LONG_TERM_YIELD_DATASET = "irt_lt_mcby_m"
EUROSTAT_LONG_TERM_YIELD_FILTERS = {
    "geo": "IT",
    "lang": "en",
}

# Eurostat government finance source for the cost of public debt.
# D41PAY is ESA 2010 interest payable by general government. Eurostat exposes
# both nominal values and values as a percentage of GDP, so the public payload
# can switch between official measures without recalculating the denominator.
EUROSTAT_DEBT_COST_DATASET = "gov_10a_main"
EUROSTAT_DEBT_COST_FILTERS = {
    "geo": "IT",
    "lang": "en",
    "na_item": "D41PAY",
    "sector": "S13",
    "unit": ["MIO_EUR", "PC_GDP"],
}
