"""Build all datasets from official sources.

Run this file from the repository root with:

python scripts/build_all_datasets.py

Settings are in scripts/config.py. The script does not use argparse and does
not use classes.
"""

import sys

from bankitalia_fpi import build_bankitalia_fpi_dataset
from eurostat_rates import build_italian_long_term_yield_dataset
from mef_treasury import build_mef_treasury_dataset
from config import PROCESSED_DIR
from io_utils import make_folder, utc_now_string, write_json


def run_pipeline_step(step_name, step_function):
    """Run one source-specific pipeline and return a status dictionary."""
    try:
        output_dir = step_function()
        return {"step": step_name, "status": "ok", "output_dir": str(output_dir), "error": ""}
    except Exception as error:
        return {"step": step_name, "status": "error", "output_dir": "", "error": str(error)}


def build_all_datasets():
    """Run Banca d'Italia, MEF/Treasury and Eurostat pipelines."""
    steps = [
        ("bankitalia_fpi", build_bankitalia_fpi_dataset),
        ("mef_treasury", build_mef_treasury_dataset),
        ("eurostat_rates", build_italian_long_term_yield_dataset),
    ]
    results = [run_pipeline_step(name, function) for name, function in steps]
    make_folder(PROCESSED_DIR)
    write_json({"generated_at_utc": utc_now_string(), "results": results}, PROCESSED_DIR / "pipeline_run_metadata.json")
    return results


def has_errors(results):
    """Return True if at least one pipeline step failed."""
    return any(result["status"] != "ok" for result in results)


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
