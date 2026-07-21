"""Banca d'Italia BDS market-rate cubes for government securities."""

import io
import zipfile
from pathlib import Path

import pandas as pd

from config import (
    BANKITALIA_A2A_BASE_URL,
    BANKITALIA_COMMUNITY,
    BANKITALIA_CONTEXT,
    BANKITALIA_FORMAT,
    BANKITALIA_LOCALE,
    BANKITALIA_MARKET_RATE_CUBES,
    CLEAN_OUTPUT,
    KEEP_RAW_FILES,
    PROCESSED_DIR,
    RAW_DIR,
)
from io_utils import clean_folder, make_folder, read_csv_bytes, request_bytes, save_bytes, utc_now_string, write_csv, write_json
from normalization_utils import parse_date_like, parse_italian_number


MARKET_RATE_SERIES = {
    "bot_12m": {
        "series_id": "MFN_RTIT.M.001.20.922",
        "label": "BOT 1 anno",
        "instrument": "BOT",
        "maturity": "12 mesi",
        "rate_kind": "Tasso lordo di aggiudicazione",
    },
    "btp_5y": {
        "series_id": "MFN_RTIT.M.020.205.922",
        "label": "BTP 5 anni",
        "instrument": "BTP",
        "maturity": "5 anni",
        "rate_kind": "Rendimento lordo all'emissione",
    },
    "btp_10y": {
        "series_id": "MFN_RTIT.M.020.210.922",
        "label": "BTP 10 anni",
        "instrument": "BTP",
        "maturity": "10 anni",
        "rate_kind": "Rendimento lordo all'emissione",
    },
    "btp_20y": {
        "series_id": "MFN_RTIT.M.020.220.922",
        "label": "BTP 20 anni",
        "instrument": "BTP",
        "maturity": "20 anni",
        "rate_kind": "Rendimento lordo all'emissione",
    },
}


def build_bankitalia_cube_url(cube_code):
    return (
        f"{BANKITALIA_A2A_BASE_URL}/{BANKITALIA_LOCALE}/{BANKITALIA_FORMAT}/"
        f"ALL/CUBE/{BANKITALIA_COMMUNITY}/{BANKITALIA_CONTEXT}/{cube_code}"
    )


def read_cube_members(zip_content):
    tables = {}
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
        for member_name in zip_file.namelist():
            if member_name.lower().endswith(".csv"):
                df, parse_info = read_csv_bytes(zip_file.read(member_name))
                tables[Path(member_name).name] = (df, parse_info)
    return tables


def legend_map(legend):
    if legend.empty or "Codice" not in legend.columns or "Descrizione" not in legend.columns:
        return {}
    return dict(zip(legend["Codice"].astype(str), legend["Descrizione"].astype(str)))


def clean_bds_date(value):
    text = str(value or "").strip().replace("/", "-")
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    return parse_date_like(text)


def build_security_issuance_yields(data, legend, source_url, downloaded_at):
    if data.empty or "DATA_OSS" not in data.columns:
        return pd.DataFrame()

    descriptions = legend_map(legend)
    records = []
    for series_key, spec in MARKET_RATE_SERIES.items():
        series_id = spec["series_id"]
        if series_id not in data.columns:
            continue
        for _, row in data.iterrows():
            value = parse_italian_number(row.get(series_id))
            date = clean_bds_date(row.get("DATA_OSS"))
            if value is None or not date:
                continue
            records.append({
                "source_institution": "Banca d'Italia",
                "source_database": "Base Dati Statistica",
                "source_cube": "RTIT0100",
                "source_cube_name": BANKITALIA_MARKET_RATE_CUBES["RTIT0100"],
                "source_url": source_url,
                "downloaded_at_utc": downloaded_at,
                "series_key": series_key,
                "series_id": series_id,
                "label": spec["label"],
                "official_label": descriptions.get(series_id, spec["label"]),
                "instrument": spec["instrument"],
                "maturity": spec["maturity"],
                "rate_kind": spec["rate_kind"],
                "date": date,
                "value_percent": round(float(value), 6),
            })

    if not records:
        return pd.DataFrame()
    out = pd.DataFrame(records)
    out["series_key"] = pd.Categorical(out["series_key"], list(MARKET_RATE_SERIES))
    out = out.sort_values(["series_key", "date"]).reset_index(drop=True)
    out["series_key"] = out["series_key"].astype(str)
    return out


def build_bankitalia_market_rates_dataset():
    output_dir = PROCESSED_DIR / "bankitalia_market"
    raw_dir = RAW_DIR / "bankitalia"
    final_dir = PROCESSED_DIR / "final"

    if CLEAN_OUTPUT:
        clean_folder(output_dir)
    else:
        make_folder(output_dir)
    make_folder(raw_dir)
    make_folder(final_dir)

    downloaded_at = utc_now_string()
    outputs = []
    for cube_code in BANKITALIA_MARKET_RATE_CUBES:
        source_url = build_bankitalia_cube_url(cube_code)
        zip_content = request_bytes(source_url)
        if KEEP_RAW_FILES:
            save_bytes(zip_content, raw_dir / f"bankitalia_{cube_code.lower()}_latest.zip")

        tables = read_cube_members(zip_content)
        data = tables.get(f"{cube_code}_DATA.csv", (pd.DataFrame(), {}))[0]
        legend = tables.get(f"{cube_code}_LEGEND.csv", (pd.DataFrame(), {}))[0]
        domain = tables.get(f"{cube_code}_DOMAIN.csv", (pd.DataFrame(), {}))[0]
        structure = tables.get(f"{cube_code}_STRUCTURE.csv", (pd.DataFrame(), {}))[0]

        write_csv(data, output_dir / f"{cube_code.lower()}_data.csv")
        write_csv(legend, output_dir / f"{cube_code.lower()}_legend.csv")
        write_csv(domain, output_dir / f"{cube_code.lower()}_domain.csv")
        write_csv(structure, output_dir / f"{cube_code.lower()}_structure.csv")

        yields = build_security_issuance_yields(data, legend, source_url, downloaded_at)
        output_path = write_csv(yields, final_dir / "security_issuance_yields.csv")
        outputs.append({"cube": cube_code, "rows": len(yields), "path": str(output_path.as_posix())})

    write_json({
        "source_institution": "Banca d'Italia",
        "source_database": "Base Dati Statistica",
        "generated_at_utc": downloaded_at,
        "outputs": outputs,
    }, output_dir / "bankitalia_market_metadata.json")
    return outputs


def main():
    outputs = build_bankitalia_market_rates_dataset()
    print(outputs)


if __name__ == "__main__":
    main()
