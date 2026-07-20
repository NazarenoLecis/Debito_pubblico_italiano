"""Build all datasets from official sources.

Run this file from the repository root with:

python scripts/build_all_datasets.py

Settings are in scripts/config.py. The script does not use argparse and does
not use classes.
"""

import sys

from bankitalia_fpi import build_bankitalia_fpi_dataset
from build_public_payload import write_public_payload
from eurostat_rates import build_italian_long_term_yield_dataset, build_italian_public_debt_cost_dataset
from mef_treasury import build_mef_treasury_dataset
from normalize_bankitalia import build_bankitalia_final_tables
from normalize_eurostat import build_eurostat_final_tables
from normalize_mef import build_mef_final_tables
from quality_checks import build_quality_report
from config import PROCESSED_DIR
from io_utils import make_folder, utc_now_string, write_json


def run_pipeline_step(step_name, step_function):
    """Run one pipeline step and return a status dictionary."""
    try:
        output = step_function()
        return {
            "step": step_name,
            "status": "ok",
            "output": str(output),
            "error": "",
        }
    except Exception as error:
        return {
            "step": step_name,
            "status": "error",
            "output": "",
            "error": str(error),
        }


def build_source_datasets():
    """Download and convert source-level datasets."""
    steps = [
        ("bankitalia_fpi", build_bankitalia_fpi_dataset),
        ("mef_treasury", build_mef_treasury_dataset),
        ("eurostat_rates", build_italian_long_term_yield_dataset),
        ("eurostat_debt_cost", build_italian_public_debt_cost_dataset),
    ]
    return [run_pipeline_step(name, function) for name, function in steps]


def build_final_datasets():
    """Build analytical final datasets from source-level CSV files."""
    steps = [
        ("normalize_bankitalia", build_bankitalia_final_tables),
        ("normalize_mef", build_mef_final_tables),
        ("normalize_eurostat", build_eurostat_final_tables),
        ("public_payload", write_public_payload),
    ]
    return [run_pipeline_step(name, function) for name, function in steps]


def run_quality_checks():
    """Build validation reports and return quality-check status."""
    report, summary = build_quality_report()
    return {
        "step": "quality_checks",
        "status": summary["status"],
        "output": summary["report_csv"],
        "error": "" if summary["status"] == "pass" else f"{summary['failed_critical_checks']} critical checks failed",
        "checks": len(report),
    }


def build_all_datasets():
    """Run source extraction, final normalization and quality checks."""
    make_folder(PROCESSED_DIR)
    results = []
    results.extend(build_source_datasets())
    results.extend(build_final_datasets())
    results.append(run_quality_checks())

    write_json({
        "generated_at_utc": utc_now_string(),
        "results": results,
    }, PROCESSED_DIR / "pipeline_run_metadata.json")
    return results


def has_errors(results):
    """Return True if at least one pipeline step failed."""
    return any(result["status"] not in ["ok", "pass"] for result in results)


def print_results(results):
    """Print a compact summary for local runs and GitHub Actions logs."""
    for result in results:
        print(result)


def main():
    results = build_all_datasets()
    print_results(results)
    if has_errors(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
