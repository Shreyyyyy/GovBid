"""Database engine/session management. SQLite for the MVP, no server required."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.models import Base

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a session that commits on normal exit.

    Callers (notably Streamlit button handlers) sometimes trigger a rerun
    with st.rerun() while still inside this context manager. Streamlit's
    rerun/stop signals are BaseException subclasses (not Exception), so we
    must commit on those too, or the change would silently roll back.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    except BaseException:
        session.commit()
        raise
    else:
        session.commit()
    finally:
        session.close()
