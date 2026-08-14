from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.domain import Card, HistoricalSale, MarketListing, Player, Prediction, Sport


def _seed_rankings_data(db: Session) -> None:
    now = datetime.now(UTC)

    basketball = Sport(name="basketball")
    football = Sport(name="football")
    db.add_all([basketball, football])
    db.flush()

    lebron = Player(name="LeBron James", sport_id=basketball.id)
    mahomes = Player(name="Patrick Mahomes", sport_id=football.id)
    brady = Player(name="Tom Brady", sport_id=football.id)
    jordan = Player(name="Michael Jordan", sport_id=basketball.id)
    db.add_all([lebron, mahomes, brady, jordan])
    db.flush()

    mover_card = Card(
        sport_id=basketball.id,
        player_id=lebron.id,
        year=2018,
        manufacturer="Panini",
        set_name="Prizm",
        card_number="23",
        is_rookie=False,
    )
    loser_card = Card(
        sport_id=football.id,
        player_id=mahomes.id,
        year=2019,
        manufacturer="Panini",
        set_name="Select",
        card_number="15",
        is_rookie=False,
    )
    loser_card_two = Card(
        sport_id=football.id,
        player_id=brady.id,
        year=2017,
        manufacturer="Topps",
        set_name="Chrome",
        card_number="12",
        is_rookie=False,
    )
    low_confidence_card = Card(
        sport_id=basketball.id,
        player_id=jordan.id,
        year=1998,
        manufacturer="Upper Deck",
        set_name="UD3",
        card_number="45",
        is_rookie=False,
    )
    insufficient_data_card = Card(
        sport_id=basketball.id,
        player_id=lebron.id,
        year=2020,
        manufacturer="Panini",
        set_name="Mosaic",
        card_number="3",
        is_rookie=False,
    )
    no_prediction_card = Card(
        sport_id=basketball.id,
        player_id=lebron.id,
        year=2021,
        manufacturer="Panini",
        set_name="Donruss",
        card_number="99",
        is_rookie=False,
    )
    db.add_all(
        [
            mover_card,
            loser_card,
            loser_card_two,
            low_confidence_card,
            insufficient_data_card,
            no_prediction_card,
        ]
    )
    db.flush()

    predictions = [
        Prediction(
            card_id=mover_card.id,
            prediction_date=now,
            prediction_horizon_days=30,
            current_price=Decimal("120.00"),
            predicted_direction="up",
            predicted_percentage_change=Decimal("12.0000"),
            confidence=Decimal("0.9100"),
            model_version="xgb-v2",
        ),
        Prediction(
            card_id=loser_card.id,
            prediction_date=now,
            prediction_horizon_days=30,
            current_price=Decimal("300.00"),
            predicted_direction="down",
            predicted_percentage_change=Decimal("-15.0000"),
            confidence=Decimal("0.9500"),
            model_version="xgb-v2",
        ),
        Prediction(
            card_id=loser_card_two.id,
            prediction_date=now,
            prediction_horizon_days=30,
            current_price=Decimal("180.00"),
            predicted_direction="down",
            predicted_percentage_change=Decimal("-8.0000"),
            confidence=Decimal("0.8200"),
            model_version="baseline-v1",
        ),
        Prediction(
            card_id=low_confidence_card.id,
            prediction_date=now,
            prediction_horizon_days=30,
            current_price=Decimal("90.00"),
            predicted_direction="up",
            predicted_percentage_change=Decimal("14.0000"),
            confidence=Decimal("0.4000"),
            model_version="xgb-v2",
        ),
        Prediction(
            card_id=insufficient_data_card.id,
            prediction_date=now,
            prediction_horizon_days=30,
            current_price=Decimal("75.00"),
            predicted_direction="up",
            predicted_percentage_change=Decimal("10.0000"),
            confidence=Decimal("0.9000"),
            model_version="xgb-v2",
        ),
    ]
    db.add_all(predictions)

    for day in range(1, 11):
        db.add(
            HistoricalSale(
                card_id=mover_card.id,
                sale_price=Decimal(str(110 + day)),
                sale_date=now - timedelta(days=day),
                marketplace="ebay",
                source="unit-test",
                currency="USD",
            )
        )
    for day in range(1, 12):
        db.add(
            HistoricalSale(
                card_id=loser_card.id,
                sale_price=Decimal(str(320 - day)),
                sale_date=now - timedelta(days=day),
                marketplace="ebay",
                source="unit-test",
                currency="USD",
            )
        )
    for day in range(1, 10):
        db.add(
            HistoricalSale(
                card_id=loser_card_two.id,
                sale_price=Decimal(str(200 - day)),
                sale_date=now - timedelta(days=day),
                marketplace="ebay",
                source="unit-test",
                currency="USD",
            )
        )
    for day in range(1, 4):
        db.add(
            HistoricalSale(
                card_id=low_confidence_card.id,
                sale_price=Decimal(str(80 + day)),
                sale_date=now - timedelta(days=day),
                marketplace="ebay",
                source="unit-test",
                currency="USD",
            )
        )

    for idx in range(4):
        db.add(
            MarketListing(
                card_id=mover_card.id,
                listing_price=Decimal("130.00"),
                marketplace="ebay",
                listing_url=f"https://example.com/mover-{idx}",
                listing_date=now - timedelta(days=idx + 1),
                is_active=True,
                currency="USD",
            )
        )
    for idx in range(3):
        db.add(
            MarketListing(
                card_id=loser_card.id,
                listing_price=Decimal("290.00"),
                marketplace="ebay",
                listing_url=f"https://example.com/loser-{idx}",
                listing_date=now - timedelta(days=idx + 1),
                is_active=True,
                currency="USD",
            )
        )
    for idx in range(3):
        db.add(
            MarketListing(
                card_id=loser_card_two.id,
                listing_price=Decimal("170.00"),
                marketplace="ebay",
                listing_url=f"https://example.com/loser-two-{idx}",
                listing_date=now - timedelta(days=idx + 1),
                is_active=True,
                currency="USD",
            )
        )

    db.commit()


def _client_with_seeded_db() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        _seed_rankings_data(session)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_movers_endpoint_returns_ranked_cards_with_required_fields() -> None:
    client = _client_with_seeded_db()

    response = client.get("/api/v1/movers", params={"min_confidence": 0.8})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["data_quality_threshold"] == 0.5
    item = payload["items"][0]
    assert item["card_name"] == "2018 Panini Prizm #23"
    assert item["player"] == "LeBron James"
    assert item["sport"] == "basketball"
    assert item["current_estimated_price"] == 120.0
    assert item["predicted_30_day_movement"] == 12.0
    assert item["predicted_direction"] == "UP"
    assert item["confidence"] == 0.91
    assert item["data_quality"] >= 0.5
    assert item["model_version"] == "xgb-v2"



def test_losers_endpoint_supports_sport_filter_and_min_sales_volume() -> None:
    client = _client_with_seeded_db()

    response = client.get(
        "/api/v1/losers",
        params={"sport": "football", "min_confidence": 0.8, "min_sales_volume": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["card_name"] == "2019 Panini Select #15"
    assert payload["items"][0]["predicted_direction"] == "DOWN"



def test_rankings_pagination_is_supported() -> None:
    client = _client_with_seeded_db()

    first_page = client.get("/api/v1/losers", params={"min_confidence": 0.8, "page": 1, "page_size": 1})
    second_page = client.get("/api/v1/losers", params={"min_confidence": 0.8, "page": 2, "page_size": 1})

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    first_payload = first_page.json()
    second_payload = second_page.json()

    assert first_payload["total"] == 2
    assert second_payload["total"] == 2
    assert len(first_payload["items"]) == 1
    assert len(second_payload["items"]) == 1
    assert first_payload["items"][0]["card_name"] != second_payload["items"][0]["card_name"]
