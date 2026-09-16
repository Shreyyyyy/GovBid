import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.ai.query_parser import ParsedQuery
from src.models import Base, Bid
from src.search.filters import apply_filters


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()

    today = dt.date.today()
    bids = [
        Bid(
            dedup_key="1", bid_id="B1", title="Desktop Computer Supply", source="demo",
            ministry="Ministry of Finance", category="Computers", status="ACTIVE",
            estimated_value=1_000_000, quantity=50, bid_end_date=today + dt.timedelta(days=5),
        ),
        Bid(
            dedup_key="2", bid_id="B2", title="Laptop Procurement", source="demo",
            ministry="Ministry of Defence", category="Computers", status="ACTIVE",
            estimated_value=5_000_000, quantity=10, bid_end_date=today + dt.timedelta(days=40),
        ),
        Bid(
            dedup_key="3", bid_id="B3", title="Office Chairs", source="demo",
            ministry="Ministry of Finance", category="Furniture", status="CLOSED",
            estimated_value=200_000, quantity=200, bid_end_date=today - dt.timedelta(days=5),
        ),
    ]
    sess.add_all(bids)
    sess.commit()
    yield sess
    sess.close()


def test_filter_by_ministry(session):
    parsed = ParsedQuery(ministry=["Ministry of Finance"])
    results = apply_filters(session.query(Bid), parsed).all()
    assert {b.bid_id for b in results} == {"B1", "B3"}


def test_filter_by_keyword(session):
    parsed = ParsedQuery(keywords=["desktop"])
    results = apply_filters(session.query(Bid), parsed).all()
    assert [b.bid_id for b in results] == ["B1"]


def test_filter_by_status(session):
    parsed = ParsedQuery(status="ACTIVE")
    results = apply_filters(session.query(Bid), parsed).all()
    assert {b.bid_id for b in results} == {"B1", "B2"}


def test_filter_by_value_range(session):
    parsed = ParsedQuery(min_value=1_000_000, max_value=2_000_000)
    results = apply_filters(session.query(Bid), parsed).all()
    assert [b.bid_id for b in results] == ["B1"]


def test_filter_by_quantity(session):
    parsed = ParsedQuery(min_quantity=100)
    results = apply_filters(session.query(Bid), parsed).all()
    assert [b.bid_id for b in results] == ["B3"]


def test_filter_combined_ministry_and_category(session):
    parsed = ParsedQuery(ministry=["Ministry of Finance"], category=["Computers"])
    results = apply_filters(session.query(Bid), parsed).all()
    assert [b.bid_id for b in results] == ["B1"]
