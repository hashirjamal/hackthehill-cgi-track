from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Float, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Item(Base):
    """Example table -- replace with your own models."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Classification(Base):
    """Output of the Laya classification layer. One row is current per complaint; older ones are history."""

    __tablename__ = "classifications"
    __table_args__ = (
        Index(
            "one_current_classification",
            "complaint_id",
            unique=True,
            sqlite_where=text("is_current"),
            postgresql_where=text("is_current"),
        ),
    )

    # Integer on SQLite (local dev), so the key autoincrements there.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    complaint_id: Mapped[str] = mapped_column(String(64), index=True)
    classifier_version: Mapped[str] = mapped_column(String(64))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    as_of_date: Mapped[date] = mapped_column(Date)

    input: Mapped[dict] = mapped_column(JSON)  # the complaint as submitted

    emergency: Mapped[bool] = mapped_column(Boolean)
    emergency_probability: Mapped[float | None] = mapped_column(Float)  # NULL when there was no text
    group_name: Mapped[str | None] = mapped_column(String(32))
    group_confidence: Mapped[float | None] = mapped_column(Float)  # Laya's top probability
    group_source: Mapped[str | None] = mapped_column(String(8))  # laya, or data on a low-confidence fallback
    laya_group: Mapped[str | None] = mapped_column(String(32))  # Laya's own pick
    subcategory: Mapped[str | None] = mapped_column(String(64))  # a Northwind data category
    subcategory_confidence: Mapped[float | None] = mapped_column(Float)
    subcategory_source: Mapped[str | None] = mapped_column(String(8))
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)  # Laya's top probability was under the threshold
    group_matches_data: Mapped[bool | None] = mapped_column(Boolean)  # NULL when the data has no category
    subcategory_matches_data: Mapped[bool | None] = mapped_column(Boolean)

    priority: Mapped[str] = mapped_column(String(2))  # P1..P3, after flags
    base_priority: Mapped[str] = mapped_column(String(2))  # before flags
    base_priority_source: Mapped[str] = mapped_column(String(16))  # data, laya or emergency
    urgency_score: Mapped[float | None] = mapped_column(Float)
    routed_team: Mapped[str] = mapped_column(String(64))
    lane: Mapped[str] = mapped_column(String(16))  # emergency, review, quick_lane, standard
    likely_cause: Mapped[str | None] = mapped_column(String(32))
    flags: Mapped[list] = mapped_column(JSON)  # flags that fired
    laya_output: Mapped[dict] = mapped_column(JSON)  # raw Laya answers, for audit
