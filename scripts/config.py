"""
Configuration for the public debt data pipeline.

The scripts do not use argparse on purpose. Change the variables in this file
when you want to modify sources, folders or behaviour.
"""

from pathlib import Path


# Root folders. All generated files stay under data/ so that they can be
# inspected, committed, ignored or published separately.
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


# General behaviour.
# KEEP_RAW_FILES=True stores the original official downloads.
# CLEAN_OUTPUT=True removes old processed outputs before rebuilding.
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
}


# MEF / Dipartimento del Tesoro source.
# The site structure changes over time. The crawler starts from official public
# debt pages, follows internal links that contain public-debt keywords and
# downloads tabular files. Keep MAX_CRAWL_PAGES conservative when testing.
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


# Eurostat source for benchmark long-term government bond yields.
# This is useful as a clean official interest-rate time series. Auction yields
# and coupon-level information are downloaded from MEF files when available.
EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
EUROSTAT_LONG_TERM_YIELD_DATASET = "irt_lt_mcby_m"
EUROSTAT_LONG_TERM_YIELD_FILTERS = {
    "geo": "IT",
    "lang": "en",
}
