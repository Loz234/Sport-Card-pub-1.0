from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.domain import HistoricalSale, MarketListing
from app.services.market_analysis import MarketAnalysisEngine


def _sale(days_ago: int, price: float) -> HistoricalSale:
    return HistoricalSale(
        card_id=1,
        sale_price=Decimal(str(price)),
        sale_date=datetime(2026, 8, 14, tzinfo=UTC) - timedelta(days=days_ago),
        marketplace="ebay",
        source="unit-test",
        currency="USD",
    )


def _listing(days_ago: int, *, active: bool = True) -> MarketListing:
    return MarketListing(
        card_id=1,
        listing_price=Decimal("100"),
        marketplace="ebay",
        listing_url=f"https://example.com/{days_ago}",
        listing_date=datetime(2026, 8, 14, tzinfo=UTC) - timedelta(days=days_ago),
        is_active=active,
        currency="USD",
    )


def test_market_analysis_engine_normal_market() -> None:
    engine = MarketAnalysisEngine()
    sales = [_sale(2, 99), _sale(6, 101), _sale(12, 100), _sale(24, 102), _sale(44, 99), _sale(70, 101)]
    sales.append(_sale(-2, 500))
    listings = [_listing(1), _listing(5), _listing(120), _listing(-1), _listing(2, active=False)]

    metrics = engine.calculate_metrics(sales=sales, listings=listings, as_of=datetime(2026, 8, 14, tzinfo=UTC))

    assert metrics.median_price_7d == pytest.approx(99, abs=1)
    assert metrics.median_price_30d == pytest.approx(100, abs=2)
    assert metrics.median_price_90d == pytest.approx(100, abs=2)
    assert metrics.average_price_7d == pytest.approx(100, abs=2)
    assert metrics.average_price_30d == pytest.approx(100, abs=2)
    assert metrics.average_price_90d == pytest.approx(100, abs=2)
    assert metrics.price_change == pytest.approx(0.0, abs=0.03)
    assert metrics.sales_volume == 6
    assert metrics.sales_velocity == pytest.approx(6 / 90)
    assert metrics.price_volatility is not None and metrics.price_volatility < 0.02
    assert metrics.active_listings == 3
    assert metrics.listing_to_sales_ratio == pytest.approx(0.5)


def test_market_analysis_engine_rising_market() -> None:
    engine = MarketAnalysisEngine()
    sales = [_sale(85, 90), _sale(60, 95), _sale(40, 100), _sale(25, 110), _sale(8, 120), _sale(2, 130)]

    metrics = engine.calculate_metrics(sales=sales, as_of=datetime(2026, 8, 14, tzinfo=UTC))

    assert metrics.price_change is not None
    assert metrics.price_change > 0
    assert metrics.average_price_7d is not None
    assert metrics.average_price_30d is not None
    assert metrics.average_price_7d > metrics.average_price_30d


def test_market_analysis_engine_falling_market() -> None:
    engine = MarketAnalysisEngine()
    sales = [_sale(85, 130), _sale(60, 120), _sale(40, 110), _sale(25, 100), _sale(8, 95), _sale(2, 90)]

    metrics = engine.calculate_metrics(sales=sales, as_of=datetime(2026, 8, 14, tzinfo=UTC))

    assert metrics.price_change is not None
    assert metrics.price_change < 0
    assert metrics.average_price_7d is not None
    assert metrics.average_price_30d is not None
    assert metrics.average_price_7d < metrics.average_price_30d


def test_market_analysis_engine_low_volume_market() -> None:
    engine = MarketAnalysisEngine()
    metrics = engine.calculate_metrics(
        sales=[_sale(4, 105)],
        listings=[_listing(3)],
        as_of=datetime(2026, 8, 14, tzinfo=UTC),
    )

    assert metrics.sales_volume == 1
    assert metrics.sales_velocity == pytest.approx(1 / 90)
    assert metrics.average_price_7d == pytest.approx(105)
    assert metrics.price_volatility is None
    assert metrics.listing_to_sales_ratio == pytest.approx(1.0)


def test_market_analysis_engine_missing_data() -> None:
    engine = MarketAnalysisEngine()
    metrics = engine.calculate_metrics(
        sales=[],
        listings=[_listing(-2), _listing(2, active=False)],
        as_of=datetime(2026, 8, 14, tzinfo=UTC),
    )

    assert metrics.median_price_7d is None
    assert metrics.median_price_30d is None
    assert metrics.median_price_90d is None
    assert metrics.average_price_7d is None
    assert metrics.average_price_30d is None
    assert metrics.average_price_90d is None
    assert metrics.price_change is None
    assert metrics.sales_volume == 0
    assert metrics.sales_velocity == 0.0
    assert metrics.price_volatility is None
    assert metrics.active_listings == 0
    assert metrics.listing_to_sales_ratio is None


def test_market_analysis_engine_outlier_detection() -> None:
    engine = MarketAnalysisEngine()
    sales = [_sale(30, 100), _sale(20, 102), _sale(10, 98), _sale(3, 101), _sale(1, 1000)]

    metrics = engine.calculate_metrics(sales=sales, as_of=datetime(2026, 8, 14, tzinfo=UTC))

    assert metrics.sales_volume == 4
    assert metrics.average_price_90d is not None
    assert metrics.average_price_90d < 150
    assert metrics.median_price_90d == pytest.approx(100, abs=2)
