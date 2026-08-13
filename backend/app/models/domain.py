from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


PredictionDirection = Literal["up", "down", "stable"]


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    players: Mapped[list["Player"]] = relationship(back_populates="sport")
    cards: Mapped[list["Card"]] = relationship(back_populates="sport")


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("sport_id", "name", name="uq_players_sport_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    sport: Mapped["Sport"] = relationship(back_populates="players")
    cards: Mapped[list["Card"]] = relationship(back_populates="player")


class GradingCompany(Base):
    __tablename__ = "grading_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    abbreviation: Mapped[str | None] = mapped_column(String(20), unique=True, default=None)

    card_variants: Mapped[list["CardVariant"]] = relationship(back_populates="grading_company")


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint(
            "sport_id",
            "player_id",
            "year",
            "manufacturer",
            "set_name",
            "card_number",
            "is_rookie",
            name="uq_card_identity",
        ),
        Index("ix_cards_player_year", "player_id", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id", ondelete="RESTRICT"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    manufacturer: Mapped[str] = mapped_column(String(120), index=True)
    set_name: Mapped[str] = mapped_column(String(255), index=True)
    card_number: Mapped[str] = mapped_column(String(50), index=True)
    is_rookie: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    sport: Mapped["Sport"] = relationship(back_populates="cards")
    player: Mapped["Player"] = relationship(back_populates="cards")
    variants: Mapped[list["CardVariant"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    historical_sales: Mapped[list["HistoricalSale"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    market_listings: Mapped[list["MarketListing"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    market_snapshots: Mapped[list["MarketSnapshot"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    watchlists: Mapped[list["Watchlist"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )


class CardVariant(Base):
    __tablename__ = "card_variants"
    __table_args__ = (
        Index("ix_card_variants_card_parallel", "card_id", "parallel"),
        UniqueConstraint(
            "card_id",
            "parallel",
            "serial_number",
            "is_autograph",
            "is_memorabilia",
            "grading_company_id",
            "grade",
            name="uq_card_variants_uniqueness",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    parallel: Mapped[str | None] = mapped_column(String(120), default=None)
    serial_number: Mapped[str | None] = mapped_column(String(50), default=None)
    is_autograph: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_memorabilia: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    grading_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("grading_companies.id", ondelete="SET NULL"),
        index=True,
        default=None,
    )
    grade: Mapped[str | None] = mapped_column(String(20), default=None)

    card: Mapped["Card"] = relationship(back_populates="variants")
    grading_company: Mapped["GradingCompany"] = relationship(back_populates="card_variants")


class HistoricalSale(Base):
    __tablename__ = "historical_sales"
    __table_args__ = (
        Index("ix_historical_sales_card_date", "card_id", "sale_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sale_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    marketplace: Mapped[str] = mapped_column(String(120), index=True)
    source: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(8), default="USD", server_default=text("'USD'"))

    card: Mapped["Card"] = relationship(back_populates="historical_sales")


class MarketListing(Base):
    __tablename__ = "market_listings"
    __table_args__ = (
        Index("ix_market_listings_card_active", "card_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    listing_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    marketplace: Mapped[str] = mapped_column(String(120), index=True)
    listing_url: Mapped[str] = mapped_column(Text)
    listing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    currency: Mapped[str] = mapped_column(String(8), default="USD", server_default=text("'USD'"))

    card: Mapped["Card"] = relationship(back_populates="market_listings")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        Index("ix_market_snapshots_card_time", "card_id", "snapshot_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    average_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    listing_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    marketplace: Mapped[str | None] = mapped_column(String(120), default=None)
    currency: Mapped[str] = mapped_column(String(8), default="USD", server_default=text("'USD'"))

    card: Mapped["Card"] = relationship(back_populates="market_snapshots")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_card_date_horizon", "card_id", "prediction_date", "prediction_horizon_days"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    prediction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    prediction_horizon_days: Mapped[int] = mapped_column(Integer, index=True)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    predicted_direction: Mapped[PredictionDirection] = mapped_column(String(10))
    predicted_percentage_change: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    model_version: Mapped[str] = mapped_column(String(120), index=True)

    card: Mapped["Card"] = relationship(back_populates="predictions")


class Watchlist(Base):
    __tablename__ = "watchlists"
    __table_args__ = (
        UniqueConstraint("watcher_id", "card_id", name="uq_watchlists_watcher_card"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    watcher_id: Mapped[str] = mapped_column(String(120), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )

    card: Mapped["Card"] = relationship(back_populates="watchlists")
