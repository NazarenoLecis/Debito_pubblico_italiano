"""Build the public data payload for nazarenolecis.com.

The payload is intentionally compact: every Banca d'Italia time series is stored
once with a small point schema, plus curated latest snapshots for public use.
"""

from pathlib import Path

import pandas as pd

from config import PROCESSED_DIR
from io_utils import utc_now_string, write_json
from normalization_utils import normalize_column_name, parse_date_like, parse_italian_number, read_csv_if_exists


PUBLIC_DIR = PROCESSED_DIR / "public"
PUBLIC_PAYLOAD_FILE = PUBLIC_DIR / "debito-pubblico.json"

TOTAL_DEBT_CODE = "FPI_FP.M.IT.S13.MGD.SBI3.101.112.FAV.EUR.EDP"
DEBT_TO_GDP_CODE = "FPI_FP.A.IT.S13.MGD.888.101.112.FAV.PGDP.EDP"

DATASET_FILES = {
    "debt_by_instrument": "debt_by_instrument.csv",
    "debt_by_holder": "debt_by_holder.csv",
    "debt_by_subsector": "debt_by_subsector.csv",
    "debt_deposits_and_liquid_assets": "debt_deposits_and_liquid_assets.csv",
    "debt_by_residual_maturity": "debt_by_residual_maturity.csv",
    "debt_by_original_maturity_currency_residency": "debt_by_original_maturity_currency_residency.csv",
    "central_government_debt_by_original_maturity_currency_residency": "central_government_debt_by_original_maturity_currency_residency.csv",
    "public_sector_borrowing_requirement_by_instrument": "public_sector_borrowing_requirement_by_instrument.csv",
    "debt_fiscal_indicators": "debt_fiscal_indicators.csv",
}

SECTION_LABELS = {
    "debt_by_instrument": "Debito per strumenti",
    "debt_by_holder": "Debito per detentori",
    "debt_by_subsector": "Debito per sottosettori",
    "debt_deposits_and_liquid_assets": "Debito, depositi e liquidita",
    "debt_by_residual_maturity": "Debito per vita residua",
    "debt_by_original_maturity_currency_residency": "Scadenza originaria, valuta e residenza",
    "central_government_debt_by_original_maturity_currency_residency": "Amministrazioni centrali",
    "public_sector_borrowing_requirement_by_instrument": "Fabbisogno per strumenti",
    "debt_fiscal_indicators": "Indicatori in percentuale del PIL",
}

COMPOSITION_CODES = {
    "debt_by_instrument": [
        "FPI_FP.M.IT.S13.F2.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.F2PO.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.F31.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.F32.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.F4.SBI2.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.F4.SBI51.101.112.FAV.EUR.EDP",
    ],
    "debt_by_holder": [
        "FPI_FP.M.IT.S13.MGD.S121.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD.S12BI1.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD.S12BI2.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD.S2.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD.SBI1.101.112.FAV.EUR.EDP",
    ],
    "debt_by_residual_maturity": [
        "FPI_FP.M.IT.S13.MGD05.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD06.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD07.SBI3.101.112.FAV.EUR.EDP",
    ],
    "debt_by_subsector": [
        "FPI_FP.M.IT.S1311.MGD.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1313.MGD.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1314.MGD.SBI3.101.112.FAV.EUR.EDP",
    ],
}

FOCUS_CODES = {
    "debt_deposits_and_liquid_assets": [
        TOTAL_DEBT_CODE,
        "FPI_FP.M.IT.S13.MGD03.SBI3.101.112.FAV.EUR.EDP",
    ],
    "debt_by_original_maturity_currency_residency": [
        "FPI_FP.M.IT.S13.MGD01.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD14.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD11.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD04.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD12.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S13.MGD13.SBI3.101.112.FAV.EUR.EDP",
    ],
    "central_government_debt_by_original_maturity_currency_residency": [
        "FPI_FP.M.IT.S1311.MGD.SBI3.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1311.MGD01.SBI4.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1311.MGD04.SBI4.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1311.MGD11.SBI4.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1311.MGD12.SBI4.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1311.MGD13.SBI4.101.112.FAV.EUR.EDP",
        "FPI_FP.M.IT.S1311.MGD14.SBI4.101.112.FAV.EUR.EDP",
    ],
}

SOURCE_COLUMNS = {
    "source_institution",
    "source_database",
    "source_publication_code",
    "source_publication_name",
    "source_table_code",
    "source_table_name",
    "source_file_kind",
    "source_zip_member",
    "source_url",
    "downloaded_at_utc",
    "source_encoding",
    "source_delimiter",
    "source_header_row",
    "standard_source",
    "standard_table_code",
    "standard_table_name",
    "standard_unit",
    "standard_date_source_column",
    "standard_value_source_column",
    "date",
    "value_mln_eur",
}


def fix_text(value):
    """Repair frequent mojibake from official CSV exports when possible."""
    text = "" if value is None else str(value)
    if any(marker in text for marker in ["Ã", "â", "Â"]):
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text
    return text


def compact_label(value):
    """Shorten repetitive official labels for chart legends."""
    text = fix_text(value)
    prefixes = [
        "Amministrazioni pubbliche: ",
        "Amministrazioni Centrali: ",
        "Amministrazioni centrali: ",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
    replacements = {
        "debito lordo": "Debito lordo",
        "titoli a medio e a lungo termine": "Titoli medio-lungo termine",
        "titoli a breve termine": "Titoli breve termine",
        "monete e depositi passivi in valuta nazionale": "Monete e depositi",
        "prestiti di banche e fondi monetari": "Prestiti banche e fondi monetari",
        "altre passivita": "Altre passivita",
        "altre passività": "Altre passivita",
        "debito lordo detenuto da ": "",
        "Debito lordo detenuto da ": "",
        "debito lordo con vita residua ": "",
        "Debito lordo con vita residua ": "",
        "altre istituzioni finanziarie monetarie": "Istituzioni finanziarie monetarie",
        "Altre istituzioni finanziarie monetarie": "Istituzioni finanziarie monetarie",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.strip(" -")
    if text:
        return text[0].upper() + text[1:]
    return text


def final_path(file_name):
    return PROCESSED_DIR / "final" / file_name


def legend_file():
    files = sorted((PROCESSED_DIR / "bankitalia" / "metadata" / "legend").glob("*.csv"))
    return files[0] if files else PROCESSED_DIR / "bankitalia" / "fpi_all_metadata.csv"


def load_legend_labels():
    legend = read_csv_if_exists(legend_file())
    if legend.empty or "Codice" not in legend.columns or "Descrizione" not in legend.columns:
        return {}, {}
    labels = {}
    official_by_column = {}
    for _, row in legend.iterrows():
        code = str(row.get("Codice", ""))
        description = str(row.get("Descrizione", ""))
        if code.startswith("FPI_FP."):
            label = fix_text(description)
            normalized = normalize_column_name(code)
            labels[code] = label
            labels[normalized] = label
            official_by_column[normalized] = code
    return labels, official_by_column


def series_columns(df):
    return [
        column
        for column in df.columns
        if (str(column).startswith("FPI_FP.") or str(column).startswith("fpi_fp_")) and column not in SOURCE_COLUMNS
    ]


def row_date(row):
    value = row.get("DATA_OSS") or row.get("data_oss") or row.get("date") or row.get("time_period")
    return parse_bds_date(value)


def parse_bds_date(value):
    """Parse BDS dates without triggering pandas warnings on YYYY/MM/DD."""
    text = "" if value is None else str(value).strip()
    if len(text) == 10 and text[4] in ["/", "-"] and text[7] in ["/", "-"]:
        return f"{text[0:4]}-{text[5:7]}-{text[8:10]}"
    if len(text) == 7 and text[4] in ["/", "-"]:
        return f"{text[0:4]}-{text[5:7]}-01"
    if len(text) == 4 and text.isdigit():
        return f"{text}-01-01"
    return parse_date_like(text)


def value_record(value):
    number = parse_italian_number(value)
    if number is None:
        return None
    return round(float(number), 3)


def point_from_row(row, column):
    date = row_date(row)
    value_mln = value_record(row.get(column))
    return point_from_value(date, value_mln)


def point_from_value(date, value_mln):
    if not date or value_mln is None:
        return None
    return [
        date,
        value_mln,
        round(value_mln / 1000, 3),
    ]


def sort_points(points):
    return sorted(points, key=lambda point: point[0])


def latest_point(points):
    ordered = sort_points(points)
    return ordered[-1] if ordered else None


def point_at_date(record, date):
    for point in record.get("points", []):
        if point[0] == date:
            return point
    return None


def latest_common_date(records):
    date_sets = []
    for record in records:
        if record:
            date_sets.append({point[0] for point in record.get("points", []) if point and point[0]})
    if not date_sets:
        return None
    common = set.intersection(*date_sets)
    return max(common) if common else None


def build_series_records(dataset, table_code, df, labels, official_by_column):
    records = []
    dates = [row_date(row) for _, row in df.iterrows()]
    for column in series_columns(df):
        official_id = official_by_column.get(column, column)
        points = []
        for date, value in zip(dates, df[column].tolist()):
            point = point_from_value(date, value_record(value))
            if point is not None:
                points.append(point)
        points = sort_points(points)
        latest = latest_point(points)
        if latest is None:
            continue
        records.append({
            "dataset": dataset,
            "section_label": SECTION_LABELS.get(dataset, dataset),
            "table_code": table_code,
            "series_id": official_id,
            "source_column": column,
            "label": compact_label(labels.get(column, labels.get(official_id, official_id))),
            "official_label": labels.get(column, labels.get(official_id, official_id)),
            "point_schema": ["date", "value_mln_eur", "value_bln_eur"],
            "points": points,
            "latest_date": latest[0],
            "latest_value_mln_eur": latest[1],
            "latest_value_bln_eur": latest[2],
        })
    return records


def find_record(records, series_id):
    for record in records:
        if record.get("series_id") == series_id:
            return record
    return None


def section_latest(records, codes):
    latest_records = []
    for code in codes:
        record = find_record(records, code)
        if record is None:
            continue
        latest_records.append({
            "series_id": code,
            "label": record["label"],
            "official_label": record["official_label"],
            "date": record["latest_date"],
            "value_mln_eur": record["latest_value_mln_eur"],
            "value_bln_eur": record["latest_value_bln_eur"],
        })
    return latest_records


def latest_composition(records, dataset):
    codes = COMPOSITION_CODES.get(dataset, [])
    selected_records = [find_record(records, code) for code in codes]
    total_record = find_record(records, TOTAL_DEBT_CODE)
    common_records = [record for record in selected_records if record]
    if total_record:
        common_records.append(total_record)
    composition_date = latest_common_date(common_records)

    rows = []
    for code, record in zip(codes, selected_records):
        if record is None:
            continue
        point = point_at_date(record, composition_date) if composition_date else latest_point(record.get("points", []))
        if point is None:
            continue
        rows.append({
            "series_id": code,
            "label": record["label"],
            "official_label": record["official_label"],
            "date": point[0],
            "value_mln_eur": point[1],
            "value_bln_eur": point[2],
        })

    total_point = point_at_date(total_record, composition_date) if total_record and composition_date else None
    total = total_point[1] if total_point else None
    if not total:
        total = sum(row["value_mln_eur"] for row in rows)
    for row in rows:
        row["share_percent"] = round(row["value_mln_eur"] / total * 100, 2) if total else None
    return sorted(rows, key=lambda row: row["value_mln_eur"], reverse=True)


def load_bankitalia_sections(labels, official_by_column):
    all_series = []
    sections = {}
    for dataset, file_name in DATASET_FILES.items():
        df = read_csv_if_exists(final_path(file_name))
        if df.empty:
            sections[dataset] = {
                "label": SECTION_LABELS.get(dataset, dataset),
                "series": [],
                "latest": [],
                "composition": [],
            }
            continue
        table_code = str(df["source_table_code"].iloc[0]) if "source_table_code" in df.columns else ""
        records = build_series_records(dataset, table_code, df, labels, official_by_column)
        all_series.extend(records)
        focus_codes = FOCUS_CODES.get(dataset, [])
        sections[dataset] = {
            "label": SECTION_LABELS.get(dataset, dataset),
            "table_code": table_code,
            "series": [record["series_id"] for record in records],
            "latest": section_latest(records, focus_codes or COMPOSITION_CODES.get(dataset, [])),
            "composition": latest_composition(records, dataset),
        }
    return all_series, sections


def build_debt_main_series(series):
    total = find_record(series, TOTAL_DEBT_CODE)
    debt_to_gdp = find_record(series, DEBT_TO_GDP_CODE)
    return {
        "total_debt": total,
        "debt_to_gdp": debt_to_gdp,
    }


def build_kpis(main_series, rates, debt_cost):
    total = main_series.get("total_debt")
    debt_to_gdp = main_series.get("debt_to_gdp")
    latest_rate = rates[-1] if rates else None
    debt_cost_latest = debt_cost.get("measures", {}).get("nominal", {}).get("latest") if debt_cost else None
    kpis = []
    if total:
        kpis.append({
            "id": "total_debt",
            "label": "Debito pubblico",
            "value": total["latest_value_bln_eur"],
            "unit": "mld euro",
            "date": total["latest_date"],
        })
    if debt_to_gdp:
        kpis.append({
            "id": "debt_to_gdp",
            "label": "Debito/PIL",
            "value": debt_to_gdp["latest_value_mln_eur"],
            "unit": "% PIL",
            "date": debt_to_gdp["latest_date"],
        })
    if latest_rate:
        kpis.append({
            "id": "long_term_yield",
            "label": "Rendimento lungo termine",
            "value": latest_rate["value"],
            "unit": "%",
            "date": latest_rate["date"],
        })
    if debt_cost_latest:
        kpis.append({
            "id": "debt_cost",
            "label": "Costo del debito",
            "value": debt_cost_latest["value_bln_eur"],
            "unit": "mld euro",
            "date": debt_cost_latest["date"],
        })
    return kpis


def latest_dict(points):
    ordered = sort_points(points)
    if not ordered:
        return None
    point = ordered[-1]
    return {
        "date": point[0],
        "value": point[1],
        "value_bln_eur": point[2] if len(point) > 2 else None,
    }


def build_interest_rates():
    df = read_csv_if_exists(PROCESSED_DIR / "eurostat" / "italy_long_term_government_bond_yield.csv")
    if df.empty:
        return []
    rows = []
    for _, row in df.iterrows():
        value = value_record(row.get("value"))
        time_value = str(row.get("time", ""))
        if value is None or not time_value:
            continue
        date = f"{time_value}-01" if len(time_value) == 7 else parse_date_like(time_value)
        rows.append({
            "date": date,
            "value": value,
            "source": "Eurostat",
            "rate_type": "long_term_government_bond_yield",
        })
    return sorted(rows, key=lambda row: row["date"])


def build_debt_cost():
    df = read_csv_if_exists(PROCESSED_DIR / "final" / "debt_interest_cost.csv")
    if df.empty:
        return {}

    nominal_points = []
    percent_points = []
    for _, row in df.iterrows():
        date = row.get("date")
        measure = row.get("cost_measure")
        if not date:
            continue
        if measure == "nominal_mln_eur":
            value_mln = value_record(row.get("value_mln_eur")) or value_record(row.get("value"))
            if value_mln is not None:
                nominal_points.append(point_from_value(date, value_mln))
        if measure == "percent_gdp":
            value = value_record(row.get("value_percent_gdp")) or value_record(row.get("value"))
            if value is not None:
                percent_points.append([date, value])

    nominal_points = [point for point in nominal_points if point is not None]
    percent_points = [point for point in percent_points if point is not None]
    nominal_points = sort_points(nominal_points)
    percent_points = sort_points(percent_points)

    return {
        "source": "Eurostat",
        "dataset": "gov_10a_main",
        "na_item": "D41PAY",
        "sector": "S13",
        "label": "Costo del debito pubblico",
        "description": "Interessi passivi delle Amministrazioni pubbliche.",
        "measures": {
            "nominal": {
                "label": "Valori nominali",
                "unit": "mld euro",
                "point_schema": ["date", "value_mln_eur", "value_bln_eur"],
                "points": nominal_points,
                "latest": latest_dict(nominal_points),
            },
            "percent_gdp": {
                "label": "Percentuale del PIL",
                "unit": "% PIL",
                "point_schema": ["date", "value_percent_gdp"],
                "points": percent_points,
                "latest": latest_dict(percent_points),
            },
        },
    }


def amount_record(value):
    number = parse_italian_number(value)
    if number is None:
        return None
    return round(float(number), 3)


def build_maturity_profile():
    df = read_csv_if_exists(PROCESSED_DIR / "final" / "treasury_maturity_profile.csv")
    if df.empty or "snapshot_date" not in df.columns:
        return {}

    snapshots = [value for value in df["snapshot_date"].astype(str).tolist() if value]
    if not snapshots:
        return {}
    snapshot_date = max(snapshots)
    latest = df[df["snapshot_date"].astype(str) == snapshot_date].copy()
    if latest.empty:
        return {}

    latest["amount_eur_revalued_num"] = latest["amount_eur_revalued"].map(amount_record)
    latest["amount_eur_nominal_num"] = latest["amount_eur_nominal"].map(amount_record) if "amount_eur_nominal" in latest.columns else None
    latest = latest[latest["amount_eur_revalued_num"].notna()]

    yearly_rows = []
    for year, group in latest.groupby("maturity_year"):
        amount_revalued = float(group["amount_eur_revalued_num"].sum())
        amount_nominal = float(group["amount_eur_nominal_num"].sum()) if "amount_eur_nominal_num" in group.columns else None
        yearly_rows.append({
            "year": str(year),
            "amount_eur_revalued": round(amount_revalued, 3),
            "amount_bln_eur_revalued": round(amount_revalued / 1_000_000_000, 3),
            "amount_eur_nominal": round(amount_nominal, 3) if amount_nominal is not None else None,
            "amount_bln_eur_nominal": round(amount_nominal / 1_000_000_000, 3) if amount_nominal is not None else None,
            "securities": int(len(group)),
        })

    quarterly_rows = []
    for (year, quarter), group in latest.groupby(["maturity_year", "maturity_quarter"]):
        amount_revalued = float(group["amount_eur_revalued_num"].sum())
        amount_nominal = float(group["amount_eur_nominal_num"].sum()) if "amount_eur_nominal_num" in group.columns else None
        quarterly_rows.append({
            "year": str(year),
            "quarter": str(quarter),
            "amount_eur_revalued": round(amount_revalued, 3),
            "amount_bln_eur_revalued": round(amount_revalued / 1_000_000_000, 3),
            "amount_eur_nominal": round(amount_nominal, 3) if amount_nominal is not None else None,
            "amount_bln_eur_nominal": round(amount_nominal / 1_000_000_000, 3) if amount_nominal is not None else None,
            "securities": int(len(group)),
        })

    yearly_rows = sorted(yearly_rows, key=lambda row: row["year"])
    quarterly_rows = sorted(quarterly_rows, key=lambda row: (row["year"], row["quarter"]))
    return {
        "source": "MEF - Dipartimento del Tesoro",
        "dataset": "Scadenze suddivise per anno",
        "snapshot_date": snapshot_date,
        "label": "Profilo scadenze",
        "description": "Ammontare dei titoli in circolazione per anno e trimestre di scadenza.",
        "value_basis": "Circolante Euro rivalutato",
        "yearly": yearly_rows,
        "quarterly": quarterly_rows,
    }


def build_sources():
    return [
        {
            "name": "Banca d'Italia",
            "dataset": "FPI",
            "url": "https://a2a.bancaditalia.it/infostat/dataservices/export/IT/CSV/ALL/PUBLICATION/BANKITALIA/DIFF/FPI",
        },
        {
            "name": "Eurostat",
            "dataset": "irt_lt_mcby_m",
            "url": "https://ec.europa.eu/eurostat/databrowser/view/irt_lt_mcby_m/default/table",
        },
        {
            "name": "Eurostat",
            "dataset": "gov_10a_main - D41PAY",
            "url": "https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table",
        },
        {
            "name": "MEF - Dipartimento del Tesoro",
            "dataset": "Debito pubblico e titoli di Stato",
            "url": "https://www.dt.mef.gov.it/it/debito_pubblico/",
        },
    ]


def build_public_payload():
    labels, official_by_column = load_legend_labels()
    series, sections = load_bankitalia_sections(labels, official_by_column)
    main_series = build_debt_main_series(series)
    rates = build_interest_rates()
    debt_cost = build_debt_cost()
    maturity_profile = build_maturity_profile()
    dates = [
        record.get("latest_date")
        for record in series
        if record.get("latest_date")
    ]
    debt_cost_latest = debt_cost.get("measures", {}).get("nominal", {}).get("latest") if debt_cost else None
    payload = {
        "meta": {
            "generated_at": utc_now_string(),
            "generated_by": "Debito_pubblico_italiano",
            "public_url": "https://data.nazarenolecis.com/debito-pubblico/data.json",
            "source_repo": "Debito_pubblico_italiano",
            "latest_bankitalia_date": max(dates) if dates else None,
            "latest_debt_cost_date": debt_cost_latest.get("date") if debt_cost_latest else None,
            "description": "Payload pubblico sul debito pubblico italiano.",
        },
        "record_schema": {
            "series_points": ["date", "value_mln_eur", "value_bln_eur"],
            "debt_cost_nominal_points": ["date", "value_mln_eur", "value_bln_eur"],
            "debt_cost_percent_gdp_points": ["date", "value_percent_gdp"],
            "maturity_profile_yearly": ["year", "amount_eur_revalued", "amount_bln_eur_revalued", "securities"],
            "maturity_profile_quarterly": ["year", "quarter", "amount_eur_revalued", "amount_bln_eur_revalued", "securities"],
        },
        "kpis": build_kpis(main_series, rates, debt_cost),
        "main_series": main_series,
        "debt_cost": debt_cost,
        "maturity_profile": maturity_profile,
        "sections": sections,
        "series": series,
        "interest_rates": rates,
        "sources": build_sources(),
        "notes": [
            "I valori monetari Banca d'Italia sono in milioni di euro; il payload espone anche miliardi di euro.",
            "Le composizioni usano le serie ufficiali selezionate per evitare doppio conteggio tra aggregati e sotto-aggregati.",
            "I tassi sono rendimenti mensili Eurostat sui titoli di Stato italiani a lungo termine.",
            "Il costo del debito e la voce Eurostat D41PAY, interessi passivi delle Amministrazioni pubbliche, in milioni di euro e in percentuale del PIL.",
            "Il profilo scadenze usa i file MEF Scadenze suddivise per anno e aggrega il circolante rivalutato per anno e trimestre di scadenza.",
        ],
    }
    return payload


def write_public_payload():
    payload = build_public_payload()
    write_json(payload, PUBLIC_PAYLOAD_FILE)
    return PUBLIC_PAYLOAD_FILE


def main():
    path = write_public_payload()
    print(f"Payload pubblico creato in {path}")


if __name__ == "__main__":
    main()
