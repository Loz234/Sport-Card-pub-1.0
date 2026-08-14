from __future__ import annotations

import pytest

from app.config import get_settings
from app.database import Base
from app.models.domain import Card, CardVariant, HistoricalSale, MarketListing, Prediction


def test_database_models_expose_expected_tables() -> None:
    table_names = set(Base.metadata.tables.keys())
    assert {
        "sports",
        "players",
        "cards",
        "card_variants",
        "grading_companies",
        "historical_sales",
        "market_listings",
        "market_snapshots",
        "predictions",
        "watchlists",
    }.issubset(table_names)


def test_card_identity_unique_constraint_exists() -> None:
    unique_constraints = {
        tuple(constraint.columns.keys())
        for constraint in Card.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert (
        "sport_id",
        "player_id",
        "year",
        "manufacturer",
        "set_name",
        "card_number",
        "is_rookie",
    ) in unique_constraints


def test_variant_and_market_indexes_exist() -> None:
    assert "ix_card_variants_card_parallel" in {index.name for index in CardVariant.__table__.indexes}
    assert "ix_historical_sales_card_date" in {index.name for index in HistoricalSale.__table__.indexes}
    assert "ix_market_listings_card_active" in {index.name for index in MarketListing.__table__.indexes}
    assert "ix_predictions_card_date_horizon" in {index.name for index in Prediction.__table__.indexes}


def test_database_url_normalizes_for_railway(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgres://postgres@host:5432/cardsignal")
    settings = get_settings()
    assert settings.database_url.startswith("postgresql+psycopg://")
    get_settings.cache_clear()


def test_sqlite_disallowed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/cardsignal.db")
    with pytest.raises(ValueError):
        get_settings()
    get_settings.cache_clear()
