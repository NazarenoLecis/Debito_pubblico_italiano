"""Normalizzazione dei dataset Eurostat.

Questo modulo costruisce dataset finali annuali/mensili provenienti da
Eurostat quando la fonte e gia tabellare e richiede solo campi standard per
il riuso applicativo.
"""

import pandas as pd

from config import PROCESSED_DIR
from normalization_utils import parse_italian_number, read_csv_if_exists, write_csv_if_not_empty


EUROSTAT_DEBT_COST_INPUT = PROCESSED_DIR / "eurostat" / "italy_public_debt_interest_cost.csv"
FINAL_DIR = PROCESSED_DIR / "final"


def build_debt_interest_cost_dataset():
    """Costruisce la serie finale del costo del debito pubblico."""
    df = read_csv_if_exists(EUROSTAT_DEBT_COST_INPUT)
    if df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["value"] = out["value"].map(parse_italian_number)
    out["value_mln_eur"] = out.apply(
        lambda row: row["value"] if row.get("unit") == "MIO_EUR" else None,
        axis=1,
    )
    out["value_bln_eur"] = out["value_mln_eur"].map(lambda value: round(value / 1000, 3) if pd.notna(value) else None)
    out["value_percent_gdp"] = out.apply(
        lambda row: row["value"] if row.get("unit") == "PC_GDP" else None,
        axis=1,
    )
    out["cost_type"] = "general_government_interest_payable"
    out["cost_type_label"] = "Interessi passivi delle Amministrazioni pubbliche"
    return out


def build_eurostat_final_tables():
    """Scrive i dataset finali Eurostat."""
    debt_cost = build_debt_interest_cost_dataset()
    outputs = []
    datasets = [
        ("debt_interest_cost.csv", debt_cost),
    ]
    for file_name, df in datasets:
        output_path = FINAL_DIR / file_name
        write_csv_if_not_empty(df, output_path)
        outputs.append({
            "dataset": file_name,
            "source": "eurostat",
            "rows": len(df),
            "path": str(output_path.as_posix()),
        })
    return outputs


def main():
    outputs = build_eurostat_final_tables()
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
