"""Build all datasets from official sources."""

from bankitalia_fpi import build_bankitalia_fpi_dataset
from eurostat_rates import build_italian_long_term_yield_dataset
from mef_treasury import build_mef_treasury_dataset


def build_all_datasets():
    results = []
    for name, func in [
        ("bankitalia_fpi", build_bankitalia_fpi_dataset),
        ("mef_treasury", build_mef_treasury_dataset),
        ("eurostat_rates", build_italian_long_term_yield_dataset),
    ]:
        try:
            output_dir = func()
            results.append({"step": name, "status": "ok", "output_dir": str(output_dir), "error": ""})
        except Exception as error:
            results.append({"step": name, "status": "error", "output_dir": "", "error": str(error)})
    return results


def main():
    for result in build_all_datasets():
        print(result)


if __name__ == "__main__":
    main()
