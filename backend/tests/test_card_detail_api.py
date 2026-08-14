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
from app.models.domain import Card, CardVariant, GradingCompany, HistoricalSale, MarketListing, MarketSnapshot, Player, Prediction, Sport


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


def _seed_card_detail_data(db: Session) -> int:
    now = datetime(2026, 8, 14, tzinfo=UTC)

    basketball = Sport(name="basketball")
    db.add(basketball)
    db.flush()

    player = Player(name="Caitlin Clark", sport_id=basketball.id)
    db.add(player)
    db.flush()

    grading_company = GradingCompany(name="Professional Sports Authenticator", abbreviation="PSA")
    db.add(grading_company)
    db.flush()

    card = Card(
        sport_id=basketball.id,
        player_id=player.id,
        year=2024,
        manufacturer="Panini",
        set_name="Prizm",
        card_number="1",
        is_rookie=True,
    )
    db.add(card)
    db.flush()

    db.add(
        CardVariant(
            card_id=card.id,
            parallel="Silver",
            grade="10",
            grading_company_id=grading_company.id,
        )
    )

    db.add_all(
        [
            _sale(card.id, 80, "96.00", now),
            _sale(card.id, 65, "98.00", now),
            _sale(card.id, 54, "99.00", now),
            _sale(card.id, 45, "100.00", now),
            _sale(card.id, 30, "100.00", now),
            _sale(card.id, 24, "101.00", now),
            _sale(card.id, 18, "99.00", now),
            _sale(card.id, 12, "102.00", now),
            _sale(card.id, 6, "125.00", now),
            _sale(card.id, 5, "128.00", now),
            _sale(card.id, 4, "130.00", now),
            _sale(card.id, 3, "132.00", now),
            _sale(card.id, 2, "135.00", now),
            _sale(card.id, 1, "138.00", now),
            _snapshot(card.id, 30, 12, "101.00", now),
            _snapshot(card.id, 21, 11, "100.00", now),
            _snapshot(card.id, 14, 10, "102.00", now),
            _snapshot(card.id, 3, 5, "129.00", now),
            _listing(card.id, "rising-1", 1, now),
            _listing(card.id, "rising-2", 2, now),
            _listing(card.id, "rising-3", 3, now),
            _listing(card.id, "rising-4", 4, now),
            Prediction(
                card_id=card.id,
                prediction_date=now,
                prediction_horizon_days=30,
                current_price=Decimal("129.00"),
                predicted_direction="up",
                predicted_percentage_change=Decimal("11.5000"),
                confidence=Decimal("0.8700"),
                model_version="xgb-v2",
            ),
            Prediction(
                card_id=card.id,
                prediction_date=now,
                prediction_horizon_days=90,
                current_price=Decimal("129.00"),
                predicted_direction="up",
                predicted_percentage_change=Decimal("18.2500"),
                confidence=Decimal("0.8300"),
                model_version="xgb-v2",
            ),
        ]
    )

    db.commit()
    return card.id


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
        _seed_card_detail_data(session)

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


def test_card_detail_endpoint_returns_historical_and_prediction_sections(client: TestClient) -> None:
    response = client.get("/api/v1/cards/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["card_id"] == 1
    assert payload["card_name"] == "2024 Panini Prizm #1"
    assert payload["player"] == "Caitlin Clark"
    assert payload["sport"] == "basketball"
    assert payload["set_name"] == "Prizm"
    assert payload["parallel"] == "Silver"
    assert payload["grade"] == "PSA 10"
    assert payload["current_estimated_market_value"] == 129.0
    assert payload["historical_market_data"]["available_ranges"] == ["7d", "30d", "90d", "1y"]
    assert len(payload["historical_market_data"]["price_points"]) == 14
    assert payload["ai_prediction"]["direction"] == "UP"
    assert payload["ai_prediction"]["predicted_30_day_movement"] == 11.5
    assert payload["ai_prediction"]["predicted_90_day_movement"] == 18.25
    assert payload["ai_prediction"]["confidence"] == 0.87
    assert payload["ai_prediction"]["sales_volume"] == 10
    assert payload["ai_prediction"]["sales_velocity"] > 0
    assert payload["ai_prediction"]["trending_score"] is not None
    assert payload["ai_prediction"]["data_quality"] in {"high", "medium", "low", "unknown"}
    assert "not guaranteed future returns or financial advice" in payload["ai_prediction"]["disclaimer"]
    assert payload["explanation"]["generated_from_validated_backend_data"] is True
    assert payload["explanation"]["summary"]
    assert payload["explanation"]["positive_signals"]
    assert payload["explanation"]["risks"]
    assert payload["explanation"]["why_model_may_be_wrong"]
    assert "certainty" in payload["explanation"]["confidence"].lower() or "probabilistic" in payload["explanation"]["confidence"].lower()


def test_add_to_watchlist_endpoint_is_idempotent(client: TestClient) -> None:
    first_response = client.post("/api/v1/cards/1/watchlist", json={"watcher_id": "demo-user"})
    second_response = client.post("/api/v1/cards/1/watchlist", json={"watcher_id": "demo-user"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == {"card_id": 1, "watcher_id": "demo-user", "added": True}
    assert second_response.json() == {"card_id": 1, "watcher_id": "demo-user", "added": False}


def test_add_to_watchlist_requires_watcher_id(client: TestClient) -> None:
    response = client.post("/api/v1/cards/1/watchlist", json={})

    assert response.status_code == 422



def test_card_detail_endpoint_returns_404_for_missing_card(client: TestClient) -> None:
    response = client.get("/api/v1/cards/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Card not found."
