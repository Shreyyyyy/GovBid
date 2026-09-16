import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Bid
from src.services.bid_service import upsert_bid


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def _normalized(**overrides):
    base = {
        "bid_id": "B1",
        "title": "Desktop Computer Supply",
        "source": "demo",
        "source_url": "https://example.com/b1",
        "organization": "Dept of Expenditure",
        "ministry": "Ministry of Finance",
        "category": "Computers",
        "status": "ACTIVE",
        "estimated_value": 1_000_000,
        "quantity": 50,
    }
    base.update(overrides)
    return base


def test_insert_new_bid(session):
    bid, created = upsert_bid(session, _normalized())
    session.commit()
    assert created is True
    assert session.query(Bid).count() == 1
    assert bid.title == "Desktop Computer Supply"


def test_duplicate_bid_id_merges_instead_of_duplicating(session):
    upsert_bid(session, _normalized())
    session.commit()

    bid2, created2 = upsert_bid(session, _normalized(source_url="https://mirror.example.com/b1"))
    session.commit()

    assert created2 is False
    assert session.query(Bid).count() == 1
    assert "https://mirror.example.com/b1" in (bid2.additional_source_urls or [])
