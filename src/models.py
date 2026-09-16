"""SQLAlchemy ORM models for GovBid Intelligence."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)

    bid_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    additional_source_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    organization: Mapped[str | None] = mapped_column(String(256), index=True, nullable=True)
    ministry: Mapped[str | None] = mapped_column(String(256), index=True, nullable=True)
    department: Mapped[str | None] = mapped_column(String(256), index=True, nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    category: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")

    bid_start_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    bid_end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)

    delivery_location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    financial_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    oem_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mse_preference: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    startup_preference: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    turnover_requirement: Mapped[str | None] = mapped_column(String(256), nullable=True)
    past_experience_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis_cache: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    documents: Mapped[list["BidDocument"]] = relationship(
        back_populates="bid", cascade="all, delete-orphan"
    )
    requirements: Mapped[list["BidRequirement"]] = relationship(
        back_populates="bid", cascade="all, delete-orphan"
    )
    source_records: Mapped[list["SourceRecord"]] = relationship(
        back_populates="bid", cascade="all, delete-orphan"
    )


class BidDocument(Base):
    __tablename__ = "bid_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id_fk: Mapped[int] = mapped_column(ForeignKey("bids.id"), index=True)

    name: Mapped[str] = mapped_column(String(512))
    doc_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_empty: Mapped[bool] = mapped_column(Boolean, default=False)
    used_ocr: Mapped[bool] = mapped_column(Boolean, default=False)

    extracted_pages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    analysis_cache: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    bid: Mapped["Bid"] = relationship(back_populates="documents")


class BidRequirement(Base):
    __tablename__ = "bid_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id_fk: Mapped[int] = mapped_column(ForeignKey("bids.id"), index=True)

    field: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(Text)
    document_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    bid: Mapped["Bid"] = relationship(back_populates="requirements")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id_fk: Mapped[int] = mapped_column(ForeignKey("bids.id"), index=True)

    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    bid: Mapped["Bid"] = relationship(back_populates="source_records")


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    query_text: Mapped[str] = mapped_column(Text)
    parsed_filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    query_text: Mapped[str] = mapped_column(Text)
    parsed_filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_status: Mapped[str] = mapped_column(
        String(64), default="Alert engine configured — notification provider can be connected later."
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    new_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
