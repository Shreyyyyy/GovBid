from src.ai.query_parser import ParsedQuery, QueryParser


class FakeGroqClient:
    """Stands in for GroqClient so tests never call the network."""

    def __init__(self, payload: dict):
        self._payload = payload

    def structured_output(self, **kwargs):
        return self._payload


def _empty_payload(**overrides) -> dict:
    payload = {
        "keywords": [],
        "organization": [],
        "ministry": [],
        "department": [],
        "category": [],
        "subcategory": [],
        "state": [],
        "city": [],
        "status": None,
        "min_value": None,
        "max_value": None,
        "min_quantity": None,
        "max_quantity": None,
        "closing_after": None,
        "closing_before": None,
        "semantic_query": None,
    }
    payload.update(overrides)
    return payload


def test_parse_extracts_category_and_ministry():
    payload = _empty_payload(
        keywords=["desktop", "computer"],
        category=["Computers"],
        ministry=["Ministry of Finance"],
    )
    parser = QueryParser(client=FakeGroqClient(payload))
    result = parser.parse("desktop computers Ministry of Finance")

    assert isinstance(result, ParsedQuery)
    assert "Computers" in result.category
    assert "Ministry of Finance" in result.ministry
    assert "desktop" in result.keywords


def test_parse_converts_currency_strings_to_numeric():
    payload = _empty_payload(min_value="10 lakh", max_value="1 crore")
    parser = QueryParser(client=FakeGroqClient(payload))
    result = parser.parse("computer bids between 10 lakh and 1 crore")

    assert result.min_value == 1_000_000
    assert result.max_value == 10_000_000


def test_parse_normalizes_status():
    payload = _empty_payload(status="active")
    parser = QueryParser(client=FakeGroqClient(payload))
    result = parser.parse("active laptop tenders")
    assert result.status == "ACTIVE"


def test_parse_empty_query_returns_default():
    parser = QueryParser(client=FakeGroqClient(_empty_payload()))
    result = parser.parse("")
    assert result == ParsedQuery()
