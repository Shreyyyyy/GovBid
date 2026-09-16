import datetime as dt

from src.utils.dates import days_until, is_closing_soon, parse_date, resolve_relative_range


def test_parse_date_iso():
    assert parse_date("2026-03-05") == dt.date(2026, 3, 5)


def test_parse_date_invalid_returns_none():
    assert parse_date("not a date") is None


def test_next_n_days():
    today = dt.date(2026, 1, 1)
    start, end = resolve_relative_range("next 15 days", today=today)
    assert start == today
    assert end == today + dt.timedelta(days=15)


def test_this_month():
    today = dt.date(2026, 2, 10)
    start, end = resolve_relative_range("this month", today=today)
    assert start == today
    assert end == dt.date(2026, 2, 28)


def test_closing_this_week():
    today = dt.date(2026, 1, 1)  # Thursday
    result = resolve_relative_range("closing this week", today=today)
    assert result is not None


def test_days_until_and_closing_soon():
    today = dt.date(2026, 1, 1)
    target = dt.date(2026, 1, 5)
    assert days_until(target, today=today) == 4
    assert is_closing_soon(target, within_days=7, today=today) is True
    assert is_closing_soon(target, within_days=2, today=today) is False
