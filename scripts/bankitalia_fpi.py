"""Pipeline Banca d'Italia per debito pubblico e fabbisogno.

Fonte: Banca d'Italia, Base Dati Statistica, pubblicazione FPI.
Output principali:
- data/processed/bankitalia/fpi_all_data.csv
- data/processed/bankitalia/fpi_core_tables.csv
- data/processed/bankitalia/fpi_catalog.csv
- data/processed/bankitalia/tables/*.csv
- data/processed/bankitalia/metadata/*.csv

Il codice non forza uno schema unico. Le tavole BDS hanno dimensioni diverse.
Per preservare tutti i dettagli, ogni file viene salvato singolarmente e poi
concatenato usando l'unione delle colonne disponibili.
"""

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from config import (
    BANKITALIA_A2A_BASE_URL,
    BANKITALIA_COMMUNITY,
    BANKITALIA_CONTENT_TYPE,
    BANKITALIA_CONTEXT,
    BANKITALIA_CORE_TABLES,
    BANKITALIA_FORMAT,
    BANKITALIA_LOCALE,
    BANKITALIA_OBJECT_TYPE,
    BANKITALIA_PUBLICATION_CODE,
    BANKITALIA_PUBLICATION_NAME,
    CLEAN_OUTPUT,
    KEEP_RAW_FILES,
    PROCESSED_DIR,
    RAW_DIR,
)
from io_utils import clean_folder, make_folder, read_csv_bytes, request_bytes, safe_filename, save_bytes, utc_now_string, write_csv, write_json


def build_bankitalia_a2a_url(object_id=None, object_type=None, content_type=None):
    """Costruisce l'URL A2A ufficiale della Base Dati Statistica."""
    object_id = object_id or BANKITALIA_PUBLICATION_CODE
    object_type = object_type or BANKITALIA_OBJECT_TYPE
    content_type = content_type or BANKITALIA_CONTENT_TYPE
    return (
        f"{BANKITALIA_A2A_BASE_URL}/{BANKITALIA_LOCALE}/{BANKITALIA_FORMAT}/"
        f"{content_type}/{object_type}/{BANKITALIA_COMMUNITY}/{BANKITALIA_CONTEXT}/{object_id}"
    )


def download_bankitalia_zip():
    """Scarica lo ZIP ufficiale della pubblicazione FPI."""
    url = build_bankitalia_a2a_url()
    content = request_bytes(url)
    if not content.startswith(b"PK"):
        preview = content[:500].decode("utf-8", errors="replace")
        raise RuntimeError(f"La risposta BDS non sembra uno ZIP. Anteprima: {preview}")
    return content, url


def infer_file_kind(member_name):
    """Classifica il file estratto dallo ZIP BDS."""
    upper_name = member_name.upper()
    for keyword in ["DATA", "LEGEND", "DOMAIN", "STRUCTURE", "METADATA"]:
        if keyword in upper_name:
            return keyword.lower()
    return "unknown"


def infer_table_code(member_name, columns):
    """Cerca un codice tavola BDS nel nome file o nelle colonne."""
    text = " ".join([member_name] + [str(column) for column in columns]).upper()
    match = re.search(r"\bTCCE\d{4}\b", text)
    if match:
        return match.group(0)
    return ""


def add_bankitalia_provenance(df, member_name, file_kind, table_code, source_url, downloaded_at, parse_info):
    """Aggiunge colonne di provenienza a una tavola Banca d'Italia."""
    out = df.copy()
    out.insert(0, "source_institution", "Banca d'Italia")
    out.insert(1, "source_database", "Base Dati Statistica")
    out.insert(2, "source_publication_code", BANKITALIA_PUBLICATION_CODE)
    out.insert(3, "source_publication_name", BANKITALIA_PUBLICATION_NAME)
    out.insert(4, "source_table_code", table_code)
    out.insert(5, "source_table_name", BANKITALIA_CORE_TABLES.get(table_code, ""))
    out.insert(6, "source_file_kind", file_kind)
    out.insert(7, "source_zip_member", member_name)
    out.insert(8, "source_url", source_url)
    out.insert(9, "downloaded_at_utc", downloaded_at)
    out.insert(10, "source_encoding", parse_info.get("encoding", ""))
    out.insert(11, "source_delimiter", parse_info.get("delimiter", ""))
    out.insert(12, "source_header_row", parse_info.get("header_row", ""))
    return out


def read_bankitalia_member(zip_file, member_name, source_url, downloaded_at):
    """Legge un CSV dentro lo ZIP BDS e restituisce una tavola arricchita."""
    raw = zip_file.read(member_name)
    df, parse_info = read_csv_bytes(raw)
    file_kind = infer_file_kind(member_name)
    table_code = infer_table_code(member_name, df.columns)
    enriched = add_bankitalia_provenance(df, member_name, file_kind, table_code, source_url, downloaded_at, parse_info)
    return enriched, file_kind, table_code


def save_bankitalia_member(df, member_name, file_kind, output_dir):
    """Salva un singolo file estratto dalla pubblicazione FPI."""
    if file_kind == "data":
        subfolder = output_dir / "tables"
    else:
        subfolder = output_dir / "metadata" / file_kind
    file_name = safe_filename(member_name, "bankitalia_member")
    if not file_name.lower().endswith(".csv"):
        file_name = f"{file_name}.csv"
    return write_csv(df, subfolder / file_name)


def process_bankitalia_zip(zip_content, source_url, output_dir):
    """Estrae dati, metadati e catalogo dalla pubblicazione FPI."""
    downloaded_at = utc_now_string()
    data_frames = []
    metadata_frames = []
    catalog_rows = []

    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
        csv_members = [name for name in zip_file.namelist() if name.lower().endswith(".csv")]
        if not csv_members:
            raise RuntimeError("Lo ZIP BDS non contiene file CSV.")

        for member_name in csv_members:
            df, file_kind, table_code = read_bankitalia_member(zip_file, member_name, source_url, downloaded_at)
            output_path = save_bankitalia_member(df, member_name, file_kind, output_dir)

            if file_kind == "data":
                data_frames.append(df)
            else:
                metadata_frames.append(df)

            catalog_rows.append({
                "source_institution": "Banca d'Italia",
                "source_publication_code": BANKITALIA_PUBLICATION_CODE,
                "source_table_code": table_code,
                "source_table_name": BANKITALIA_CORE_TABLES.get(table_code, ""),
                "source_file_kind": file_kind,
                "source_zip_member": member_name,
                "rows": len(df),
                "columns": len(df.columns),
                "output_csv": str(Path(output_path).as_posix()),
            })

    if data_frames:
        all_data = pd.concat(data_frames, ignore_index=True, sort=False)
        write_csv(all_data, output_dir / "fpi_all_data.csv")
        core_data = all_data[all_data["source_table_code"].isin(BANKITALIA_CORE_TABLES.keys())].copy()
        write_csv(core_data, output_dir / "fpi_core_tables.csv")

    if metadata_frames:
        all_metadata = pd.concat(metadata_frames, ignore_index=True, sort=False)
        write_csv(all_metadata, output_dir / "fpi_all_metadata.csv")

    catalog = pd.DataFrame(catalog_rows)
    write_csv(catalog, output_dir / "fpi_catalog.csv")
    return catalog_rows


def build_bankitalia_fpi_dataset():
    """Esegue l'intera pipeline Banca d'Italia FPI."""
    output_dir = PROCESSED_DIR / "bankitalia"
    raw_dir = RAW_DIR / "bankitalia"

    if CLEAN_OUTPUT:
        clean_folder(output_dir)
    else:
        make_folder(output_dir)
    make_folder(raw_dir)

    zip_content, source_url = download_bankitalia_zip()
    if KEEP_RAW_FILES:
        save_bytes(zip_content, raw_dir / "bankitalia_fpi_latest.zip")

    catalog_rows = process_bankitalia_zip(zip_content, source_url, output_dir)
    write_json({
        "source_institution": "Banca d'Italia",
        "source_database": "Base Dati Statistica",
        "source_publication_code": BANKITALIA_PUBLICATION_CODE,
        "source_publication_name": BANKITALIA_PUBLICATION_NAME,
        "source_url": source_url,
        "tables_of_interest": BANKITALIA_CORE_TABLES,
        "generated_files": catalog_rows,
        "generated_at_utc": utc_now_string(),
    }, output_dir / "fpi_run_metadata.json")

    return output_dir


def main():
    """Entry point manuale. Modificare scripts/config.py per cambiare opzioni."""
    output_dir = build_bankitalia_fpi_dataset()
    print(f"Output Banca d'Italia creato in {output_dir}")


if __name__ == "__main__":
    main()
