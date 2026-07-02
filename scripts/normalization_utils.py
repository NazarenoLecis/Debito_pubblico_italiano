"""Funzioni condivise per costruire dataset analitici finali.

Le fonti ufficiali hanno layout diversi. Queste utility servono a:
- pulire nomi di colonne;
- convertire numeri italiani;
- estrarre date;
- trovare colonne probabili senza imporre uno schema fragile;
- salvare CSV finali con colonne stabili.
"""

import re
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError


SOURCE_PREFIXES = ["source_", "downloaded_at_"]


def clean_text(value):
    """Restituisce testo normalizzato per confronti e ricerche."""
    if pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_column_name(value):
    """Converte un nome colonna in snake_case stabile."""
    text = clean_text(value).lower()
    replacements = {
        "à": "a",
        "è": "e",
        "é": "e",
        "ì": "i",
        "ò": "o",
        "ù": "u",
        "€": "eur",
        "%": "pct",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "column"


def normalize_columns(df):
    """Rinomina colonne duplicate mantenendo tutti i campi."""
    seen = {}
    new_columns = []
    for column in df.columns:
        base = normalize_column_name(column)
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count == 1:
            new_columns.append(base)
        else:
            new_columns.append(f"{base}_{count}")
    out = df.copy()
    out.columns = new_columns
    return out


def is_source_column(column):
    """Identifica colonne di provenienza aggiunte dalla pipeline."""
    return any(str(column).startswith(prefix) for prefix in SOURCE_PREFIXES)


def first_existing_column(df, candidates):
    """Trova la prima colonna disponibile tra una lista di candidati."""
    normalized = {normalize_column_name(column): column for column in df.columns}
    for candidate in candidates:
        key = normalize_column_name(candidate)
        if key in normalized:
            return normalized[key]
    return None


def columns_containing(df, keywords):
    """Restituisce le colonne il cui nome contiene almeno una keyword."""
    matches = []
    for column in df.columns:
        normalized = normalize_column_name(column)
        if any(keyword in normalized for keyword in keywords):
            matches.append(column)
    return matches


def parse_italian_number(value):
    """Converte numeri con separatori italiani in float.

    Esempi gestiti:
    - 1.234,56
    - 1 234,56
    - (1.234,56)
    - 3,45%
    - n.d.
    """
    text = clean_text(value)
    if text == "":
        return None

    lower = text.lower()
    if lower in ["-", "--", "n.d.", "nd", "na", "n/a", "nan", "none"]:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    text = text.replace("%", "")
    text = text.replace("€", "")
    text = text.replace(" ", "")
    text = re.sub(r"[^0-9,.-]", "", text)

    if text.count(",") == 1 and text.count(".") >= 1:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    elif text.count(",") > 1 and text.count(".") == 0:
        text = text.replace(",", "")

    if text in ["", ".", "-", "-."]:
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if negative:
        number = -number
    return number


def parse_percent(value):
    """Converte una percentuale lasciando il valore in punti percentuali."""
    return parse_italian_number(value)


def parse_date_like(value):
    """Converte date frequenti nelle fonti italiane in formato ISO."""
    text = clean_text(value)
    if text == "":
        return ""

    for dayfirst in [True, False]:
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
        if not pd.isna(parsed):
            return parsed.date().isoformat()

    month_match = re.match(r"^(\d{4})[-/](\d{1,2})$", text)
    if month_match:
        year, month = month_match.groups()
        return f"{int(year):04d}-{int(month):02d}-01"

    return ""


def extract_isin(text):
    """Estrae il primo ISIN italiano presente in un testo."""
    match = re.search(r"\bIT[0-9A-Z]{10}\b", clean_text(text).upper())
    if match:
        return match.group(0)
    return ""


def extract_all_isins(text):
    """Estrae tutti gli ISIN italiani presenti in un testo."""
    return re.findall(r"\bIT[0-9A-Z]{10}\b", clean_text(text).upper())


def infer_security_type(text):
    """Inferisce la tipologia di titolo da testo libero."""
    upper = clean_text(text).upper()
    patterns = [
        ("BTP_VALORE", ["BTP VALORE"]),
        ("BTP_ITALIA", ["BTP ITALIA"]),
        ("BTP_EI", ["BTP€I", "BTP I", "BTP INDICIZZ", "BTP€"]),
        ("CCTEU", ["CCTEU", "CCT-EU", "CCT EU"]),
        ("CTZ", ["CTZ"]),
        ("BOT", ["BOT"]),
        ("BTP", ["BTP"]),
    ]
    for security_type, keywords in patterns:
        if any(keyword in upper for keyword in keywords):
            return security_type
    return ""


def extract_candidate_dates(text):
    """Estrae date testuali frequenti da una riga MEF."""
    text = clean_text(text)
    patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{4}\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
    ]
    dates = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            parsed = parse_date_like(match)
            if parsed and parsed not in dates:
                dates.append(parsed)
    return dates


def join_row_values(row):
    """Concatena i valori non vuoti di una riga."""
    values = []
    for value in row:
        text = clean_text(value)
        if text:
            values.append(text)
    return " | ".join(values)


def read_csv_if_exists(path):
    """Legge un CSV se esiste, altrimenti restituisce un DataFrame vuoto."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    if path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except EmptyDataError:
        return pd.DataFrame()


def write_csv_if_not_empty(df, path):
    """Scrive un CSV anche quando il DataFrame è vuoto.

    I file vuoti vengono creati a dimensione zero. Questo evita EmptyDataError
    nei controlli qualità quando una fonte non produce righe.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if df is None or df.empty:
        path.write_text("", encoding="utf-8")
    else:
        df.to_csv(path, index=False, encoding="utf-8")
    return path


def add_numeric_copy(df, source_column, target_column):
    """Aggiunge una colonna numerica partendo da una colonna testuale."""
    out = df.copy()
    if source_column and source_column in out.columns:
        out[target_column] = out[source_column].map(parse_italian_number)
    else:
        out[target_column] = None
    return out


def add_date_copy(df, source_column, target_column):
    """Aggiunge una colonna data ISO partendo da una colonna testuale."""
    out = df.copy()
    if source_column and source_column in out.columns:
        out[target_column] = out[source_column].map(parse_date_like)
    else:
        out[target_column] = ""
    return out
