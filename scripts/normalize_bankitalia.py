"""Normalizzazione dei dati Banca d'Italia FPI.

Questo modulo costruisce dataset finali a partire dai CSV source-level generati
da bankitalia_fpi.py. Le tavole BDS possono avere colonne diverse. Il codice
mantiene tutte le colonne originali e aggiunge campi standard quando riesce a
riconoscerli.
"""

import pandas as pd

from config import BANKITALIA_CORE_TABLES, PROCESSED_DIR
from normalization_utils import (
    add_date_copy,
    add_numeric_copy,
    columns_containing,
    first_existing_column,
    normalize_columns,
    read_csv_if_exists,
    write_csv_if_not_empty,
)


BANKITALIA_INPUT = PROCESSED_DIR / "bankitalia" / "fpi_core_tables.csv"
FINAL_DIR = PROCESSED_DIR / "final"

DATE_CANDIDATES = [
    "time_period",
    "periodo",
    "data",
    "date",
    "time",
    "mese",
    "anno_mese",
]

VALUE_CANDIDATES = [
    "obs_value",
    "value",
    "valore",
    "valori",
    "amount",
    "importo",
]


FINAL_TABLES = {
    "TCCE0125": "public_sector_borrowing_requirement_by_instrument.csv",
    "TCCE0175": "debt_by_instrument.csv",
    "TCCE0200": "debt_by_holder.csv",
    "TCCE0225": "debt_by_subsector.csv",
    "TCCE0300": "debt_deposits_and_liquid_assets.csv",
    "TCCE0325": "debt_by_residual_maturity.csv",
    "TCCE0350": "debt_by_original_maturity_currency_residency.csv",
    "TCCE0375": "central_government_debt_by_original_maturity_currency_residency.csv",
}


def load_bankitalia_core_data():
    """Carica il CSV core della pubblicazione FPI."""
    df = read_csv_if_exists(BANKITALIA_INPUT)
    if df.empty:
        return df
    return normalize_columns(df)


def get_standard_columns(df):
    """Trova colonne candidate per data e valore numerico."""
    date_column = first_existing_column(df, DATE_CANDIDATES)
    value_column = first_existing_column(df, VALUE_CANDIDATES)

    if value_column is None:
        numeric_like = columns_containing(df, ["value", "valore", "amount", "importo", "obs"])
        value_column = numeric_like[0] if numeric_like else None

    return date_column, value_column


def add_standard_fields(df, source_table_code):
    """Aggiunge campi standard a una tavola Banca d'Italia."""
    out = df.copy()
    date_column, value_column = get_standard_columns(out)

    out["standard_source"] = "Banca d'Italia BDS"
    out["standard_table_code"] = source_table_code
    out["standard_table_name"] = BANKITALIA_CORE_TABLES.get(source_table_code, "")
    out["standard_unit"] = "million_eur"
    out["standard_date_source_column"] = date_column or ""
    out["standard_value_source_column"] = value_column or ""

    out = add_date_copy(out, date_column, "date")
    out = add_numeric_copy(out, value_column, "value_mln_eur")
    return out


def filter_table(df, table_code):
    """Filtra una tavola BDS usando source_table_code."""
    if df.empty or "source_table_code" not in df.columns:
        return pd.DataFrame()
    return df[df["source_table_code"] == table_code].copy()


def build_bankitalia_final_tables():
    """Costruisce i dataset finali Banca d'Italia sotto data/processed/final."""
    df = load_bankitalia_core_data()
    outputs = []

    for table_code, file_name in FINAL_TABLES.items():
        table = filter_table(df, table_code)
        table = add_standard_fields(table, table_code) if not table.empty else table
        output_path = FINAL_DIR / file_name
        write_csv_if_not_empty(table, output_path)
        outputs.append({
            "dataset": file_name,
            "source": "bankitalia_fpi",
            "table_code": table_code,
            "rows": len(table),
            "path": str(output_path.as_posix()),
        })

    debt_total = build_debt_total_monthly(df)
    debt_total_path = FINAL_DIR / "debt_total_monthly.csv"
    write_csv_if_not_empty(debt_total, debt_total_path)
    outputs.append({
        "dataset": "debt_total_monthly.csv",
        "source": "bankitalia_fpi",
        "table_code": "TCCE0175",
        "rows": len(debt_total),
        "path": str(debt_total_path.as_posix()),
    })

    return outputs


def build_debt_total_monthly(df):
    """Crea una serie mensile del debito partendo dalla tavola strumenti.

    La funzione cerca righe con indicazioni di totale. Se la struttura della
    tavola non rende il totale riconoscibile, restituisce tutta la tavola
    TCCE0175 con campi standard. Questo evita perdite di informazione.
    """
    table = filter_table(df, "TCCE0175")
    if table.empty:
        return table

    standard = add_standard_fields(table, "TCCE0175")
    text_columns = [column for column in standard.columns if column not in ["value_mln_eur"]]
    total_mask = pd.Series(False, index=standard.index)

    for column in text_columns:
        values = standard[column].astype(str).str.lower()
        total_mask = total_mask | values.str.contains("totale|total|debito delle amministrazioni pubbliche", regex=True, na=False)

    filtered = standard[total_mask].copy()
    if filtered.empty:
        return standard
    return filtered


def main():
    outputs = build_bankitalia_final_tables()
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
