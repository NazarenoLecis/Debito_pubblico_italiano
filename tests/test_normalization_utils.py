import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from normalization_utils import extract_isin, infer_security_type, parse_italian_number, parse_date_like


def test_parse_italian_number_decimal_comma():
    assert parse_italian_number("1.234,56") == 1234.56


def test_parse_italian_number_parentheses_negative():
    assert parse_italian_number("(1.234,56)") == -1234.56


def test_parse_italian_number_percentage_points():
    assert parse_italian_number("3,45%") == 3.45


def test_extract_isin():
    assert extract_isin("BTP IT0000000001") == "IT0000000001"


def test_infer_security_type():
    assert infer_security_type("BTP Valore maggio 2030") == "BTP_VALORE"
    assert infer_security_type("BOT 12 mesi") == "BOT"


def test_parse_date_like():
    assert parse_date_like("31/12/2026") == "2026-12-31"
