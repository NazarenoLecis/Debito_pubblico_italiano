"""Controlli qualità della pipeline debito pubblico.

I controlli distinguono tra errori critici e warning. Un errore critico blocca il
workflow. Un warning viene scritto nel report e consente di ispezionare la fonte
senza perdere l'intero aggiornamento.
"""

import json
from pathlib import Path

import pandas as pd

from config import PROCESSED_DIR
from normalization_utils import read_csv_if_exists, write_csv_if_not_empty


QUALITY_DIR = PROCESSED_DIR / "quality"

CRITICAL_FILES = [
    PROCESSED_DIR / "bankitalia" / "fpi_all_data.csv",
    PROCESSED_DIR / "bankitalia" / "fpi_core_tables.csv",
    PROCESSED_DIR / "mef" / "mef_download_catalog.csv",
    PROCESSED_DIR / "eurostat" / "italy_long_term_government_bond_yield.csv",
    PROCESSED_DIR / "eurostat" / "italy_public_debt_interest_cost.csv",
    PROCESSED_DIR / "final" / "debt_by_instrument.csv",
    PROCESSED_DIR / "final" / "interest_rates.csv",
    PROCESSED_DIR / "final" / "debt_interest_cost.csv",
    PROCESSED_DIR / "final" / "treasury_maturity_profile.csv",
]

WARNING_FILES = [
    PROCESSED_DIR / "final" / "debt_by_holder.csv",
    PROCESSED_DIR / "final" / "debt_by_residual_maturity.csv",
    PROCESSED_DIR / "final" / "debt_by_original_maturity_currency_residency.csv",
    PROCESSED_DIR / "final" / "treasury_securities_by_isin.csv",
    PROCESSED_DIR / "final" / "treasury_auctions.csv",
    PROCESSED_DIR / "final" / "treasury_redemptions.csv",
]


def count_rows(path):
    """Conta le righe di un CSV se esiste."""
    df = read_csv_if_exists(path)
    return len(df), list(df.columns)


def check_file_not_empty(path, severity):
    """Controlla che un file esista e contenga almeno una riga."""
    path = Path(path)
    if not path.exists():
        return {
            "check": "file_exists",
            "path": str(path.as_posix()),
            "severity": severity,
            "status": "fail",
            "rows": 0,
            "message": "file missing",
        }

    rows, _ = count_rows(path)
    if rows == 0:
        return {
            "check": "file_not_empty",
            "path": str(path.as_posix()),
            "severity": severity,
            "status": "fail",
            "rows": rows,
            "message": "file has zero rows",
        }

    return {
        "check": "file_not_empty",
        "path": str(path.as_posix()),
        "severity": severity,
        "status": "pass",
        "rows": rows,
        "message": "ok",
    }


def check_required_columns(path, columns, severity="critical"):
    """Controlla che un CSV contenga colonne richieste."""
    df = read_csv_if_exists(path)
    missing = [column for column in columns if column not in df.columns]
    return {
        "check": "required_columns",
        "path": str(Path(path).as_posix()),
        "severity": severity,
        "status": "fail" if missing else "pass",
        "rows": len(df),
        "message": ";".join(missing) if missing else "ok",
    }


def check_mef_downloads():
    """Verifica che il crawler MEF abbia scaricato almeno un file ufficiale."""
    path = PROCESSED_DIR / "mef" / "mef_download_catalog.csv"
    df = read_csv_if_exists(path)
    if df.empty:
        return {
            "check": "mef_downloaded_files",
            "path": str(path.as_posix()),
            "severity": "critical",
            "status": "fail",
            "rows": 0,
            "message": "MEF catalogue is empty",
        }

    if "status" in df.columns:
        ok_rows = df[df["status"] == "ok"]
    else:
        ok_rows = df

    return {
        "check": "mef_downloaded_files",
        "path": str(path.as_posix()),
        "severity": "critical",
        "status": "pass" if len(ok_rows) > 0 else "fail",
        "rows": len(ok_rows),
        "message": "ok" if len(ok_rows) > 0 else "no MEF file downloaded successfully",
    }


def check_no_duplicate_dates(path, date_column="date", severity="warning"):
    """Controlla duplicati su una colonna data quando disponibile."""
    df = read_csv_if_exists(path)
    if df.empty or date_column not in df.columns:
        return {
            "check": "duplicate_dates",
            "path": str(Path(path).as_posix()),
            "severity": severity,
            "status": "skip",
            "rows": len(df),
            "message": "date column missing or file empty",
        }

    non_empty = df[df[date_column].astype(str).str.len() > 0]
    duplicates = non_empty[non_empty.duplicated([date_column], keep=False)]
    return {
        "check": "duplicate_dates",
        "path": str(Path(path).as_posix()),
        "severity": severity,
        "status": "pass" if duplicates.empty else "fail",
        "rows": len(duplicates),
        "message": "ok" if duplicates.empty else "duplicate date values found",
    }


def build_quality_report():
    """Esegue tutti i controlli e salva report CSV e JSON."""
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    checks = []

    for path in CRITICAL_FILES:
        checks.append(check_file_not_empty(path, "critical"))

    for path in WARNING_FILES:
        checks.append(check_file_not_empty(path, "warning"))

    checks.append(check_mef_downloads())
    checks.append(check_required_columns(PROCESSED_DIR / "final" / "debt_by_instrument.csv", ["standard_table_code", "value_mln_eur"], "critical"))
    checks.append(check_required_columns(PROCESSED_DIR / "final" / "interest_rates.csv", ["rate_source", "rate_type"], "critical"))
    checks.append(check_required_columns(PROCESSED_DIR / "final" / "debt_interest_cost.csv", ["date", "cost_measure", "value"], "critical"))
    checks.append(check_required_columns(PROCESSED_DIR / "final" / "treasury_maturity_profile.csv", ["snapshot_date", "maturity_year", "amount_eur_revalued"], "critical"))
    checks.append(check_no_duplicate_dates(PROCESSED_DIR / "final" / "debt_total_monthly.csv", "date", "warning"))

    report = pd.DataFrame(checks)
    report_path = QUALITY_DIR / "validation_report.csv"
    write_csv_if_not_empty(report, report_path)

    failed_critical = report[(report["severity"] == "critical") & (report["status"] == "fail")]
    summary = {
        "checks": len(report),
        "failed_critical_checks": len(failed_critical),
        "status": "fail" if len(failed_critical) > 0 else "pass",
        "report_csv": str(report_path.as_posix()),
    }
    (QUALITY_DIR / "validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, summary


def assert_quality_passed():
    """Blocca la pipeline se esistono errori critici."""
    _, summary = build_quality_report()
    if summary["status"] != "pass":
        raise RuntimeError(f"Quality checks failed: {summary['failed_critical_checks']} critical checks failed")
    return summary


def main():
    report, summary = build_quality_report()
    print(report)
    print(summary)
    if summary["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
