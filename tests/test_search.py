import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.ai.query_parser import ParsedQuery
from src.models import Base, Bid
from src.search.search_engine import SearchEngine


class FakeParser:
    def parse(self, query: str) -> ParsedQuery:
        return ParsedQuery(category=["Computers"])


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    sess.add_all(
        [
            Bid(dedup_key="1", bid_id="B1", title="Desktop Computer", source="demo", category="Computers", status="ACTIVE"),
            Bid(dedup_key="2", bid_id="B2", title="Office Chairs", source="demo", category="Furniture", status="ACTIVE"),
        ]
    )
    sess.commit()
    yield sess
    sess.close()


def test_search_engine_uses_parser_and_filters(session):
    engine = SearchEngine(query_parser=FakeParser())
    response = engine.search(session, "computer bids", use_semantic=False)
    assert response.total == 1
    assert response.bids[0].bid_id == "B1"
