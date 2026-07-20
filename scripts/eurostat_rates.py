"""Eurostat public-finance pipeline.

This module downloads the Eurostat monthly long-term government bond yield
series for Italy. It complements Treasury auction/rate files with a clean,
official benchmark interest-rate time series.

It also downloads annual general-government interest payable from Eurostat
`gov_10a_main`, which is used as the historical cost of public debt.

No argparse and no classes are used. Change settings in scripts/config.py.
"""

import itertools

import pandas as pd
import requests

from config import (
    EUROSTAT_BASE_URL,
    EUROSTAT_DEBT_COST_DATASET,
    EUROSTAT_DEBT_COST_FILTERS,
    EUROSTAT_LONG_TERM_YIELD_DATASET,
    EUROSTAT_LONG_TERM_YIELD_FILTERS,
    PROCESSED_DIR,
    REQUEST_TIMEOUT_SECONDS,
)
from io_utils import make_folder, utc_now_string, write_csv, write_json
from normalization_utils import parse_date_like


def build_eurostat_url(dataset_code):
    """Build the Eurostat dissemination API URL for a dataset."""
    return f"{EUROSTAT_BASE_URL}/{dataset_code}"


def download_eurostat_json(dataset_code, filters):
    """Download a Eurostat JSON-stat payload."""
    response = requests.get(build_eurostat_url(dataset_code), params=filters, timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise RuntimeError(f"Eurostat download failed: HTTP {response.status_code}\n{response.text[:500]}")
    return response.json(), response.url


def get_dimension_values(payload, dimension_name):
    """Return ordered labels for one JSON-stat dimension."""
    dimension = payload["dimension"][dimension_name]
    categories = dimension["category"]
    index_map = categories["index"]
    labels = categories.get("label", {})
    ordered_codes = sorted(index_map, key=lambda code: index_map[code])
    return [(code, labels.get(code, code)) for code in ordered_codes]


def get_jsonstat_value(values, linear_index):
    """Read values from dense list payloads or sparse dictionary payloads."""
    if isinstance(values, list):
        if linear_index >= len(values):
            return None
        return values[linear_index]
    if isinstance(values, dict):
        return values.get(str(linear_index))
    return None


def flatten_jsonstat(payload):
    """Convert a compact JSON-stat payload into a rectangular DataFrame."""
    dimension_names = payload["id"]
    size = payload["size"]
    dimension_values = [get_dimension_values(payload, name) for name in dimension_names]
    values = payload.get("value", {})
    rows = []

    for linear_index, coordinates in enumerate(itertools.product(*[range(length) for length in size])):
        value = get_jsonstat_value(values, linear_index)
        if value is None:
            continue
        row = {"value": value}
        for dimension_name, coordinate, possible_values in zip(dimension_names, coordinates, dimension_values):
            code, label = possible_values[coordinate]
            row[dimension_name] = code
            row[f"{dimension_name}_label"] = label
        rows.append(row)

    return pd.DataFrame(rows)


def annual_date(value):
    """Convert an annual Eurostat time code into an ISO date."""
    text = "" if value is None else str(value).strip()
    if len(text) == 4 and text.isdigit():
        return f"{text}-01-01"
    return parse_date_like(text)


def add_source_columns(df, dataset_code, source_url):
    """Add common source metadata to one Eurostat DataFrame."""
    out = df.copy()
    if not out.empty:
        out.insert(0, "source_institution", "Eurostat")
        out.insert(1, "source_dataset", dataset_code)
        out.insert(2, "source_url", source_url)
        out.insert(3, "downloaded_at_utc", utc_now_string())
    return out


def build_italian_long_term_yield_dataset():
    """Download and save Italian long-term government bond yields."""
    output_dir = PROCESSED_DIR / "eurostat"
    make_folder(output_dir)

    payload, source_url = download_eurostat_json(EUROSTAT_LONG_TERM_YIELD_DATASET, EUROSTAT_LONG_TERM_YIELD_FILTERS)
    df = add_source_columns(flatten_jsonstat(payload), EUROSTAT_LONG_TERM_YIELD_DATASET, source_url)

    write_csv(df, output_dir / "italy_long_term_government_bond_yield.csv")
    write_json({
        "source_institution": "Eurostat",
        "source_dataset": EUROSTAT_LONG_TERM_YIELD_DATASET,
        "filters": EUROSTAT_LONG_TERM_YIELD_FILTERS,
        "source_url": source_url,
        "generated_at_utc": utc_now_string(),
        "output": "italy_long_term_government_bond_yield.csv",
    }, output_dir / "eurostat_rates_metadata.json")
    return output_dir


def build_italian_public_debt_cost_dataset():
    """Download and save Italian general-government interest payable."""
    output_dir = PROCESSED_DIR / "eurostat"
    make_folder(output_dir)

    payload, source_url = download_eurostat_json(EUROSTAT_DEBT_COST_DATASET, EUROSTAT_DEBT_COST_FILTERS)
    df = add_source_columns(flatten_jsonstat(payload), EUROSTAT_DEBT_COST_DATASET, source_url)

    if not df.empty:
        df["date"] = df["time"].map(annual_date)
        df["year"] = df["time"].astype(str)
        df["cost_measure"] = df["unit"].map({
            "MIO_EUR": "nominal_mln_eur",
            "PC_GDP": "percent_gdp",
        }).fillna(df["unit"])

    write_csv(df, output_dir / "italy_public_debt_interest_cost.csv")
    write_json({
        "source_institution": "Eurostat",
        "source_dataset": EUROSTAT_DEBT_COST_DATASET,
        "filters": EUROSTAT_DEBT_COST_FILTERS,
        "source_url": source_url,
        "generated_at_utc": utc_now_string(),
        "output": "italy_public_debt_interest_cost.csv",
    }, output_dir / "eurostat_debt_cost_metadata.json")
    return output_dir


def main():
    output_dir = build_italian_long_term_yield_dataset()
    build_italian_public_debt_cost_dataset()
    print(f"Eurostat output created in {output_dir}")


if __name__ == "__main__":
    main()
