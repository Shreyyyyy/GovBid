from src.utils.currency import parse_inr, format_inr


def test_lakh_conversion():
    assert parse_inr("₹10 lakh") == 1_000_000
    assert parse_inr("10 lakhs") == 1_000_000


def test_crore_conversion():
    assert parse_inr("1 crore") == 10_000_000
    assert parse_inr("₹1 crore") == 10_000_000


def test_plain_grouped_number():
    assert parse_inr("₹1,25,00,000") == 1_25_00_000


def test_none_and_empty():
    assert parse_inr(None) is None
    assert parse_inr("") is None


def test_numeric_passthrough():
    assert parse_inr(500000) == 500000.0


def test_format_inr_uses_crore_and_lakh():
    assert "crore" in format_inr(15_000_000)
    assert "lakh" in format_inr(200_000)
    assert format_inr(None) == "N/A"
