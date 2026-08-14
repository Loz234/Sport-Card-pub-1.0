from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.domain import Card, HistoricalSale, MarketListing, MarketSnapshot, Player, Sport
from app.services.trending import TrendingCardsEngine


def _sale(card_id: int, days_ago: int, price: str, now: datetime) -> HistoricalSale:
    return HistoricalSale(
        card_id=card_id,
        sale_price=Decimal(price),
        sale_date=now - timedelta(days=days_ago),
        marketplace="ebay",
        source="unit-test",
        currency="USD",
    )


def _listing(card_id: int, suffix: str, days_ago: int, now: datetime) -> MarketListing:
    return MarketListing(
        card_id=card_id,
        listing_price=Decimal("125.00"),
        marketplace="ebay",
        listing_url=f"https://example.com/{suffix}",
        listing_date=now - timedelta(days=days_ago),
        is_active=True,
        currency="USD",
    )


def _snapshot(card_id: int, days_ago: int, listing_count: int, average_price: str, now: datetime) -> MarketSnapshot:
    return MarketSnapshot(
        card_id=card_id,
        snapshot_at=now - timedelta(days=days_ago),
        average_price=Decimal(average_price),
        min_price=Decimal(average_price) - Decimal("5.00"),
        max_price=Decimal(average_price) + Decimal("5.00"),
        listing_count=listing_count,
        marketplace="ebay",
        currency="USD",
    )


def _seed_trending_data(db: Session) -> None:
    now = datetime(2026, 8, 14, tzinfo=UTC)

    basketball = Sport(name="basketball")
    football = Sport(name="football")
    db.add_all([basketball, football])
    db.flush()

    rising_player = Player(name="Caitlin Clark", sport_id=basketball.id)
    falling_player = Player(name="Joe Burrow", sport_id=football.id)
    sparse_player = Player(name="Victor Wembanyama", sport_id=basketball.id)
    db.add_all([rising_player, falling_player, sparse_player])
    db.flush()

    rising_card = Card(
        sport_id=basketball.id,
        player_id=rising_player.id,
        year=2024,
        manufacturer="Panini",
        set_name="Prizm",
        card_number="1",
        is_rookie=True,
    )
    falling_card = Card(
        sport_id=football.id,
        player_id=falling_player.id,
        year=2021,
        manufacturer="Panini",
        set_name="Select",
        card_number="9",
        is_rookie=False,
    )
    sparse_card = Card(
        sport_id=basketball.id,
        player_id=sparse_player.id,
        year=2024,
        manufacturer="Topps",
        set_name="Chrome",
        card_number="77",
        is_rookie=True,
    )
    db.add_all([rising_card, falling_card, sparse_card])
    db.flush()

    db.add_all(
        [
            _sale(rising_card.id, 80, "96.00", now),
            _sale(rising_card.id, 65, "98.00", now),
            _sale(rising_card.id, 54, "99.00", now),
            _sale(rising_card.id, 45, "100.00", now),
            _sale(rising_card.id, 30, "100.00", now),
            _sale(rising_card.id, 24, "101.00", now),
            _sale(rising_card.id, 18, "99.00", now),
            _sale(rising_card.id, 12, "102.00", now),
            _sale(rising_card.id, 6, "125.00", now),
            _sale(rising_card.id, 5, "128.00", now),
            _sale(rising_card.id, 4, "130.00", now),
            _sale(rising_card.id, 3, "132.00", now),
            _sale(rising_card.id, 2, "135.00", now),
            _sale(rising_card.id, 1, "138.00", now),
            _snapshot(rising_card.id, 30, 12, "101.00", now),
            _snapshot(rising_card.id, 21, 11, "100.00", now),
            _snapshot(rising_card.id, 14, 10, "102.00", now),
            _snapshot(rising_card.id, 3, 5, "129.00", now),
            _listing(rising_card.id, "rising-1", 1, now),
            _listing(rising_card.id, "rising-2", 2, now),
            _listing(rising_card.id, "rising-3", 3, now),
            _listing(rising_card.id, "rising-4", 4, now),
            _sale(falling_card.id, 84, "212.00", now),
            _sale(falling_card.id, 70, "214.00", now),
            _sale(falling_card.id, 60, "209.00", now),
            _sale(falling_card.id, 50, "211.00", now),
            _sale(falling_card.id, 33, "228.00", now),
            _sale(falling_card.id, 28, "230.00", now),
            _sale(falling_card.id, 20, "225.00", now),
            _sale(falling_card.id, 15, "222.00", now),
            _sale(falling_card.id, 6, "185.00", now),
            _sale(falling_card.id, 5, "180.00", now),
            _sale(falling_card.id, 4, "178.00", now),
            _sale(falling_card.id, 3, "175.00", now),
            _sale(falling_card.id, 2, "170.00", now),
            _sale(falling_card.id, 1, "168.00", now),
            _sale(sparse_card.id, 5, "300.00", now),
            _sale(sparse_card.id, 2, "310.00", now),
            _sale(sparse_card.id, 1, "315.00", now),
        ]
    )

    db.commit()


@pytest.fixture
def client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with session_local() as session:
        _seed_trending_data(session)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client_instance = TestClient(app)
    try:
        yield client_instance
    finally:
        app.dependency_overrides.pop(get_db, None)
        client_instance.close()
        engine.dispose()


def test_trending_engine_only_returns_cards_with_sufficient_data() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    try:
        with session_local() as session:
            _seed_trending_data(session)
            items = TrendingCardsEngine(session).get_trending()

        card_names = {item.card_name for item in items}
        assert "2024 Panini Prizm #1" in card_names
        assert "2021 Panini Select #9" in card_names
        assert "2024 Topps Chrome #77" not in card_names
    finally:
        engine.dispose()


def test_trending_endpoint_returns_signals_without_inventing_missing_supply_data(client: TestClient) -> None:
    response = client.get("/api/trending")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2

    by_name = {item["card_name"]: item for item in payload["items"]}

    rising = by_name["2024 Panini Prizm #1"]
    assert rising["player"] == "Caitlin Clark"
    assert rising["sport"] == "basketball"
    assert rising["trending_score"] >= 45
    assert rising["price_momentum"] > 0
    assert rising["sales_momentum"] > 0
    assert rising["supply_signal"] > 0
    assert rising["activity_signal"] > 0

    falling = by_name["2021 Panini Select #9"]
    assert falling["player"] == "Joe Burrow"
    assert falling["sport"] == "football"
    assert falling["trending_score"] >= 45
    assert falling["price_momentum"] < 0
    assert falling["sales_momentum"] > 0
    assert falling["supply_signal"] is None
    assert falling["activity_signal"] > 0


def test_trending_endpoint_is_available_under_versioned_api_prefix(client: TestClient) -> None:
    response = client.get("/api/v1/trending")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
