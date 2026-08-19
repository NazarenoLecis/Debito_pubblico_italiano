"""Verify that the public JSON endpoint is aligned with the local build."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


LOCAL_PAYLOAD_FILE = Path("output/data/public/debito-pubblico.json")
PUBLIC_ENDPOINT_URL = os.getenv(
    "PUBLIC_ENDPOINT_URL",
    "https://data.nazarenolecis.com/debito-pubblico/data.json",
)
MAX_ENDPOINT_AGE_HOURS = float(os.getenv("PUBLIC_ENDPOINT_MAX_AGE_HOURS", "168"))
REQUEST_TIMEOUT_SECONDS = 60

REQUIRED_TOP_LEVEL_KEYS = [
    "debt_cost",
    "kpis",
    "main_series",
    "maturity_profile",
    "meta",
    "security_yields",
]
SOURCE_DATE_FIELDS = [
    "latest_bankitalia_date",
    "latest_debt_cost_date",
]


def load_json_file(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fetch_public_payload():
    request = Request(PUBLIC_ENDPOINT_URL, headers={"User-Agent": "debt-data-pipeline/1.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def parse_utc_timestamp(value):
    if not value:
        raise ValueError("timestamp pubblico mancante")
    normalized = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def kpi_dates_by_id(payload):
    dates = {}
    for record in payload.get("kpis", []):
        identifier = record.get("id")
        date = record.get("date")
        if identifier and date:
            dates[identifier] = date
    return dates


def assert_required_keys(payload):
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
    if missing:
        raise AssertionError("endpoint pubblico incompleto: " + ", ".join(missing))


def assert_endpoint_is_fresh(public_payload):
    generated_at = parse_utc_timestamp(public_payload.get("meta", {}).get("generated_at"))
    age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600
    if age_hours > MAX_ENDPOINT_AGE_HOURS:
        raise AssertionError(
            f"endpoint pubblico troppo vecchio: {age_hours:.1f} ore "
            f"(limite {MAX_ENDPOINT_AGE_HOURS:.1f})"
        )


def assert_source_dates_not_older(local_payload, public_payload):
    local_meta = local_payload.get("meta", {})
    public_meta = public_payload.get("meta", {})
    stale_fields = []
    for field in SOURCE_DATE_FIELDS:
        local_date = local_meta.get(field)
        public_date = public_meta.get(field)
        if local_date and public_date and public_date < local_date:
            stale_fields.append(f"{field}: pubblico {public_date}, locale {local_date}")
    if stale_fields:
        raise AssertionError("endpoint pubblico non allineato alle fonti: " + "; ".join(stale_fields))


def assert_kpi_dates_not_older(local_payload, public_payload):
    local_dates = kpi_dates_by_id(local_payload)
    public_dates = kpi_dates_by_id(public_payload)
    stale_kpis = []
    for identifier, local_date in local_dates.items():
        public_date = public_dates.get(identifier)
        if public_date and public_date < local_date:
            stale_kpis.append(f"{identifier}: pubblico {public_date}, locale {local_date}")
    if stale_kpis:
        raise AssertionError("KPI pubblici non allineati: " + "; ".join(stale_kpis))


def main():
    local_payload = load_json_file(LOCAL_PAYLOAD_FILE)
    public_payload = fetch_public_payload()
    assert_required_keys(public_payload)
    assert_endpoint_is_fresh(public_payload)
    assert_source_dates_not_older(local_payload, public_payload)
    assert_kpi_dates_not_older(local_payload, public_payload)
    meta = public_payload.get("meta", {})
    print("Endpoint pubblico verificato:", PUBLIC_ENDPOINT_URL)
    print("generated_at:", meta.get("generated_at"))
    print("latest_bankitalia_date:", meta.get("latest_bankitalia_date"))


if __name__ == "__main__":
    main()
