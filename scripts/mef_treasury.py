"""MEF / Treasury parser for detailed government securities data.

This module converts the official Treasury files found by mef_discovery.py into
CSV outputs. It keeps two representations:

1. wide tables, close to the original source layout;
2. one-row-per-cell tables, useful for files with complex headers, notes or
   multiple table blocks.

This preserves the maximum detail for ISIN, security type, issue date, maturity,
rates, auction yield, coupons, outstanding amounts and redemptions whenever
those fields are present in the original files.
"""

from pathlib import Path

import pandas as pd

from config import CLEAN_OUTPUT, PROCESSED_DIR
from io_utils import clean_folder, extract_zip, make_folder, read_csv_bytes, safe_filename, write_csv, write_json, utc_now_string
from mef_discovery import build_mef_discovery_catalog


def source_info_from_catalog_row(row, local_file, sheet_name="", source_format=""):
    """Create provenance columns for a Treasury table or sheet."""
    return {
        "source_institution": "MEF - Dipartimento del Tesoro",
        "source_url": row.get("url", ""),
        "source_page": row.get("source_page", ""),
        "source_label": row.get("label", ""),
        "source_file": str(local_file),
        "source_sheet": sheet_name,
        "source_format": source_format,
    }


def add_source_columns(df, source_info):
    """Add provenance columns before original columns."""
    out = df.copy()
    for key, value in reversed(list(source_info.items())):
        out.insert(0, key, value)
    return out


def table_to_cell_rows(df, source_info):
    """Convert any table into row-column-value format without losing cells."""
    records = []
    df = df.fillna("").reset_index(drop=True)
    for row_number, row in df.iterrows():
        for column_number, value in enumerate(row.tolist(), start=1):
            record = dict(source_info)
            record["row_number"] = row_number + 1
            record["column_number"] = column_number
            record["value"] = str(value)
            records.append(record)
    return pd.DataFrame(records)


def normalise_columns(df):
    """Assign stable column names when the original file has no clean header."""
    df = df.fillna("")
    df.columns = [str(column).strip() if str(column).strip() else f"col_{index + 1}" for index, column in enumerate(df.columns)]
    return df


def read_excel_workbook(path):
    """Read every sheet from an Excel workbook as strings."""
    workbook = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    output = {}
    for sheet_name, df in workbook.items():
        df = df.fillna("")
        df.columns = [f"col_{index + 1}" for index in range(len(df.columns))]
        output[str(sheet_name)] = df
    return output


def process_csv_source(path, row, output_dir):
    """Process a Treasury CSV file."""
    df, parse_info = read_csv_bytes(Path(path).read_bytes())
    df = normalise_columns(df)
    info = source_info_from_catalog_row(row, path, source_format="csv")
    info["source_encoding"] = parse_info.get("encoding", "")
    info["source_delimiter"] = parse_info.get("delimiter", "")
    wide = add_source_columns(df, info)
    cells = table_to_cell_rows(df, info)
    stem = safe_filename(Path(path).stem, "mef_csv")
    write_csv(wide, output_dir / "files" / f"{stem}_wide.csv")
    write_csv(cells, output_dir / "files" / f"{stem}_cells.csv")
    return [wide], [cells]


def process_excel_source(path, row, output_dir):
    """Process every sheet in a Treasury Excel file."""
    wide_frames = []
    cell_frames = []
    for sheet_name, df in read_excel_workbook(Path(path)).items():
        info = source_info_from_catalog_row(row, path, sheet_name=sheet_name, source_format=Path(path).suffix.lower().replace(".", ""))
        wide = add_source_columns(df, info)
        cells = table_to_cell_rows(df, info)
        stem = safe_filename(f"{Path(path).stem}_{sheet_name}", "mef_excel")
        write_csv(wide, output_dir / "files" / f"{stem}_wide.csv")
        write_csv(cells, output_dir / "files" / f"{stem}_cells.csv")
        wide_frames.append(wide)
        cell_frames.append(cells)
    return wide_frames, cell_frames


def process_zip_source(path, row, output_dir):
    """Extract a Treasury ZIP and process tabular files inside it."""
    extracted = extract_zip(Path(path), output_dir / "zip_extracted" / safe_filename(Path(path).stem, "zip"))
    wide_frames = []
    cell_frames = []
    for child_path in extracted:
        child_row = dict(row)
        child_row["url"] = f"{row.get('url', '')}#{child_path.name}"
        if child_path.suffix.lower() == ".csv":
            wide, cells = process_csv_source(child_path, child_row, output_dir)
        elif child_path.suffix.lower() in [".xlsx", ".xls"]:
            wide, cells = process_excel_source(child_path, child_row, output_dir)
        else:
            continue
        wide_frames.extend(wide)
        cell_frames.extend(cells)
    return wide_frames, cell_frames


def process_catalog_row(row, output_dir):
    """Process one downloaded file from the MEF download catalogue."""
    local_file = row.get("local_file", "")
    if not local_file or row.get("status") != "ok":
        return [], []
    path = Path(local_file)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return process_csv_source(path, row, output_dir)
    if suffix in [".xlsx", ".xls"]:
        return process_excel_source(path, row, output_dir)
    if suffix == ".zip":
        return process_zip_source(path, row, output_dir)
    return [], []


def has_successful_downloads(catalog):
    """Return True when the MEF discovery step downloaded at least one file."""
    if catalog.empty or "status" not in catalog.columns:
        return False
    return len(catalog[catalog["status"] == "ok"]) > 0


def build_mef_treasury_dataset():
    """Run discovery, download and conversion of Treasury tabular files."""
    output_dir = PROCESSED_DIR / "mef"
    if CLEAN_OUTPUT:
        clean_folder(output_dir)
    else:
        make_folder(output_dir)
    make_folder(output_dir / "files")

    catalog = build_mef_discovery_catalog()
    if not has_successful_downloads(catalog):
        raise RuntimeError("No MEF Treasury files were downloaded successfully.")

    wide_frames = []
    cell_frames = []

    for row in catalog.to_dict("records"):
        try:
            wide, cells = process_catalog_row(row, output_dir)
            wide_frames.extend(wide)
            cell_frames.extend(cells)
        except Exception as error:
            error_row = pd.DataFrame([{**row, "processing_error": str(error)}])
            write_csv(error_row, output_dir / "files" / f"error_{len(wide_frames) + len(cell_frames)}.csv")

    if wide_frames:
        write_csv(pd.concat(wide_frames, ignore_index=True, sort=False), output_dir / "mef_all_tables_wide.csv")
    if cell_frames:
        write_csv(pd.concat(cell_frames, ignore_index=True, sort=False), output_dir / "mef_all_cells_long.csv")

    write_json({
        "source_institution": "MEF - Dipartimento del Tesoro",
        "generated_at_utc": utc_now_string(),
        "purpose": "Detailed government securities data: ISIN, type, auctions, rates, yields, maturities and redemptions when available in official files.",
        "outputs": ["mef_download_catalog.csv", "mef_all_tables_wide.csv", "mef_all_cells_long.csv", "files/*.csv"],
    }, output_dir / "mef_run_metadata.json")
    return output_dir


def main():
    output_dir = build_mef_treasury_dataset()
    print(f"MEF output created in {output_dir}")


if __name__ == "__main__":
    main()
