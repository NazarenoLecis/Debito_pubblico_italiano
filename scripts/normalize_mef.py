"""Normalizzazione dei file MEF / Dipartimento del Tesoro.

Il MEF pubblica file con layout non sempre omogenei. Questo modulo costruisce
file finali robusti partendo dal formato cella-per-riga generato da
mef_treasury.py. L'obiettivo è estrarre le informazioni più utili senza perdere
il contesto originale.
"""

import re

import pandas as pd

from config import PROCESSED_DIR
from normalization_utils import (
    clean_text,
    extract_all_isins,
    extract_candidate_dates,
    infer_security_type,
    parse_italian_number,
    read_csv_if_exists,
    write_csv_if_not_empty,
)


MEF_CELLS_INPUT = PROCESSED_DIR / "mef" / "mef_all_cells_long.csv"
MEF_WIDE_INPUT = PROCESSED_DIR / "mef" / "mef_all_tables_wide.csv"
EUROSTAT_RATES_INPUT = PROCESSED_DIR / "eurostat" / "italy_long_term_government_bond_yield.csv"
FINAL_DIR = PROCESSED_DIR / "final"


AUCTION_KEYWORDS = ["asta", "aste", "auction", "emissione", "emissioni", "rendimento", "tasso"]
REDEMPTION_KEYWORDS = ["rimborso", "rimborsi", "scadenza", "scadenze", "maturity", "redemption"]
RATE_KEYWORDS = ["tasso", "rendimento", "yield", "cedola", "coupon"]


def load_mef_cells():
    """Carica il file MEF cella-per-riga."""
    return read_csv_if_exists(MEF_CELLS_INPUT)


def load_mef_wide():
    """Carica il file MEF wide."""
    return read_csv_if_exists(MEF_WIDE_INPUT)


def make_row_context(cells):
    """Ricostruisce il contenuto di ogni riga originale."""
    if cells.empty:
        return pd.DataFrame()

    required = ["source_file", "source_sheet", "row_number", "column_number", "value"]
    missing = [column for column in required if column not in cells.columns]
    if missing:
        return pd.DataFrame()

    df = cells.copy()
    df["column_number_num"] = pd.to_numeric(df["column_number"], errors="coerce")
    df = df.sort_values(["source_file", "source_sheet", "row_number", "column_number_num"])

    group_cols = ["source_institution", "source_url", "source_page", "source_label", "source_file", "source_sheet", "row_number"]
    group_cols = [column for column in group_cols if column in df.columns]

    rows = []
    for keys, group in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys))
        values = [clean_text(value) for value in group["value"].tolist()]
        values = [value for value in values if value]
        record["row_text"] = " | ".join(values)
        for _, cell in group.iterrows():
            column_number = int(float(cell["column_number_num"])) if not pd.isna(cell["column_number_num"]) else 0
            if column_number > 0:
                record[f"col_{column_number}"] = clean_text(cell["value"])
        rows.append(record)

    return pd.DataFrame(rows)


def contains_keyword(text, keywords):
    """Verifica se una riga contiene una delle parole chiave."""
    lower = clean_text(text).lower()
    return any(keyword.lower() in lower for keyword in keywords)


def remove_isins_from_text(text):
    """Rimuove gli ISIN dal testo prima dell'estrazione numerica."""
    return re.sub(r"\bIT[0-9A-Z]{10}\b", " ", clean_text(text).upper())


def extract_first_number_from_text(text):
    """Estrae il primo numero interpretabile da testo libero ignorando gli ISIN."""
    cleaned = remove_isins_from_text(text)
    candidates = re.findall(r"\(?-?\d[\d. ]*(?:,\d+)?%?\)?", cleaned)
    for candidate in candidates:
        parsed = parse_italian_number(candidate)
        if parsed is not None:
            return parsed
    return None


def build_treasury_securities_by_isin(row_context):
    """Costruisce un dataset con una riga per ISIN individuato nei file MEF."""
    if row_context.empty or "row_text" not in row_context.columns:
        return pd.DataFrame()

    records = []
    for _, row in row_context.iterrows():
        isins = extract_all_isins(row.get("row_text", ""))
        if not isins:
            continue
        dates = extract_candidate_dates(row.get("row_text", ""))
        for isin in isins:
            record = row.to_dict()
            record["isin"] = isin
            record["security_type"] = infer_security_type(row.get("row_text", ""))
            record["candidate_date_1"] = dates[0] if len(dates) > 0 else ""
            record["candidate_date_2"] = dates[1] if len(dates) > 1 else ""
            record["candidate_date_3"] = dates[2] if len(dates) > 2 else ""
            record["candidate_numeric_value"] = extract_first_number_from_text(row.get("row_text", ""))
            records.append(record)

    return pd.DataFrame(records)


def build_keyword_dataset(row_context, keywords, dataset_name):
    """Filtra righe MEF usando keyword e aggiunge campi standard."""
    if row_context.empty or "row_text" not in row_context.columns:
        return pd.DataFrame()

    mask = row_context["row_text"].map(lambda text: contains_keyword(text, keywords))
    out = row_context[mask].copy()
    if out.empty:
        return out

    out["dataset_name"] = dataset_name
    out["security_type"] = out["row_text"].map(infer_security_type)
    out["isin"] = out["row_text"].map(lambda text: ";".join(extract_all_isins(text)))
    out["candidate_date_1"] = out["row_text"].map(lambda text: extract_candidate_dates(text)[0] if extract_candidate_dates(text) else "")
    out["candidate_numeric_value"] = out["row_text"].map(extract_first_number_from_text)
    return out


def build_interest_rates_dataset():
    """Crea un dataset tassi unendo benchmark Eurostat e righe MEF sui tassi."""
    eurostat = read_csv_if_exists(EUROSTAT_RATES_INPUT)
    frames = []

    if not eurostat.empty:
        eurostat_out = eurostat.copy()
        eurostat_out["rate_source"] = "Eurostat"
        eurostat_out["rate_type"] = "long_term_government_bond_yield"
        frames.append(eurostat_out)

    cells = load_mef_cells()
    context = make_row_context(cells)
    mef_rates = build_keyword_dataset(context, RATE_KEYWORDS, "mef_rates_raw")
    if not mef_rates.empty:
        mef_rates["rate_source"] = "MEF - Dipartimento del Tesoro"
        mef_rates["rate_type"] = "auction_or_coupon_rate_raw"
        frames.append(mef_rates)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def build_mef_final_tables():
    """Costruisce i dataset finali MEF sotto data/processed/final."""
    cells = load_mef_cells()
    context = make_row_context(cells)

    securities = build_treasury_securities_by_isin(context)
    auctions = build_keyword_dataset(context, AUCTION_KEYWORDS, "treasury_auctions_raw")
    redemptions = build_keyword_dataset(context, REDEMPTION_KEYWORDS, "treasury_redemptions_raw")
    rates = build_interest_rates_dataset()

    outputs = []
    datasets = [
        ("treasury_securities_by_isin.csv", securities),
        ("treasury_auctions.csv", auctions),
        ("treasury_redemptions.csv", redemptions),
        ("interest_rates.csv", rates),
    ]

    for file_name, df in datasets:
        output_path = FINAL_DIR / file_name
        write_csv_if_not_empty(df, output_path)
        outputs.append({
            "dataset": file_name,
            "source": "mef_treasury" if file_name != "interest_rates.csv" else "mef_treasury_eurostat",
            "rows": len(df),
            "path": str(output_path.as_posix()),
        })

    return outputs


def main():
    outputs = build_mef_final_tables()
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
