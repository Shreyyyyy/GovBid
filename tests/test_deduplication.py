from src.utils.deduplication import dedup_key, find_duplicate, normalize_title


def test_normalize_title_strips_punctuation_and_case():
    assert normalize_title("Desktop Computers (Core i5)!") == "desktop computers core i5"


def test_dedup_key_prefers_bid_id():
    key = dedup_key("BID-123", "gem", "https://example.com/a", "Title", "Org")
    assert key == "bid_id:bid-123"


def test_dedup_key_falls_back_to_url():
    key = dedup_key(None, "cppp", "https://example.com/tender/1", "Title", "Org")
    assert key.startswith("url:")


def test_dedup_key_falls_back_to_title_org():
    key = dedup_key(None, "ministry", None, "Desktop Computers", "Ministry of Finance")
    assert key.startswith("title_org:")


def test_find_duplicate_matches_same_bid_id():
    existing = [{"bid_id": "BID-1", "source": "gem", "source_url": None, "title": "A", "organization": "X"}]
    new_bid = {"bid_id": "BID-1", "source": "gem", "source_url": None, "title": "A different title", "organization": "Y"}
    assert find_duplicate(new_bid, existing) is not None


def test_find_duplicate_no_match():
    existing = [{"bid_id": "BID-1", "source": "gem", "source_url": None, "title": "A", "organization": "X"}]
    new_bid = {"bid_id": "BID-2", "source": "gem", "source_url": None, "title": "B", "organization": "Y"}
    assert find_duplicate(new_bid, existing) is None
