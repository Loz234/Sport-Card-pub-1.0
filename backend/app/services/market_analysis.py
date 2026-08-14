from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import exp, log
from statistics import median, pstdev
from typing import Iterable

from app.models.domain import HistoricalSale, MarketListing


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class MarketSignalSummary:
    movers_ready: bool = True
    losers_ready: bool = True
    trending_ready: bool = True
    predictions_ready: bool = False


@dataclass(frozen=True)
class MarketMetrics:
    median_price_7d: float | None
    median_price_30d: float | None
    median_price_90d: float | None
    average_price_7d: float | None
    average_price_30d: float | None
    average_price_90d: float | None
    price_change: float | None
    sales_volume: int
    sales_velocity: float
    price_volatility: float | None
    active_listings: int
    listing_to_sales_ratio: float | None


@dataclass(frozen=True)
class _SalePoint:
    price: float
    sale_date: datetime


class MarketAnalysisEngine:
    def __init__(self, *, half_life_days: float = 30.0, outlier_z_threshold: float = 3.5) -> None:
        self.half_life_days = max(1.0, half_life_days)
        self.outlier_z_threshold = outlier_z_threshold

    def calculate_metrics(
        self,
        *,
        sales: Iterable[HistoricalSale],
        as_of: datetime,
        listings: Iterable[MarketListing] | None = None,
    ) -> MarketMetrics:
        as_of_utc = _to_utc(as_of)
        valid_sales = self._sales_up_to_date(sales=sales, as_of=as_of_utc)

        sales_7d = self._window_sales(valid_sales=valid_sales, as_of=as_of_utc, days=7)
        raw_sales_30d = self._window_sales(valid_sales=valid_sales, as_of=as_of_utc, days=30)
        raw_sales_90d = self._window_sales(valid_sales=valid_sales, as_of=as_of_utc, days=90)

        sales_7d = self._remove_outliers(sales_7d)
        sales_30d = self._remove_outliers(raw_sales_30d)
        sales_90d = self._remove_outliers(raw_sales_90d)
        baseline_sales = self._remove_outliers(self._window_sales_excluding_recent(valid_sales, as_of_utc, days=30, recent_days=7))

        avg_7d = self._weighted_average(sales_7d, as_of_utc)
        avg_30d = self._weighted_average(sales_30d, as_of_utc)
        avg_90d = self._weighted_average(sales_90d, as_of_utc)
        baseline_avg = self._weighted_average(baseline_sales, as_of_utc)
        if baseline_avg in (None, 0.0):
            baseline_avg = avg_90d

        price_change = None
        if avg_7d is not None and baseline_avg not in (None, 0.0):
            price_change = (avg_7d - baseline_avg) / baseline_avg

        volume = len(raw_sales_30d)
        velocity = volume / 30 if volume else 0.0
        volatility = self._volatility(sales_90d)

        active_listings = self._active_listing_count(listings=listings, as_of=as_of_utc)
        listing_to_sales_ratio = (active_listings / volume) if volume else None

        return MarketMetrics(
            median_price_7d=self._weighted_median(sales_7d, as_of_utc),
            median_price_30d=self._weighted_median(sales_30d, as_of_utc),
            median_price_90d=self._weighted_median(sales_90d, as_of_utc),
            average_price_7d=avg_7d,
            average_price_30d=avg_30d,
            average_price_90d=avg_90d,
            price_change=price_change,
            sales_volume=volume,
            sales_velocity=velocity,
            price_volatility=volatility,
            active_listings=active_listings,
            listing_to_sales_ratio=listing_to_sales_ratio,
        )

    def _sales_up_to_date(self, *, sales: Iterable[HistoricalSale], as_of: datetime) -> list[_SalePoint]:
        points: list[_SalePoint] = []
        for sale in sales:
            sale_date = _to_utc(sale.sale_date)
            if sale_date > as_of:
                continue
            price = float(sale.sale_price)
            if price <= 0:
                continue
            points.append(_SalePoint(price=price, sale_date=sale_date))
        return points

    def _window_sales(self, *, valid_sales: list[_SalePoint], as_of: datetime, days: int) -> list[_SalePoint]:
        start = as_of - timedelta(days=days)
        return [sale for sale in valid_sales if sale.sale_date >= start]

    def _window_sales_excluding_recent(
        self,
        valid_sales: list[_SalePoint],
        as_of: datetime,
        *,
        days: int,
        recent_days: int,
    ) -> list[_SalePoint]:
        start = as_of - timedelta(days=days)
        recent_boundary = as_of - timedelta(days=recent_days)
        return [sale for sale in valid_sales if start <= sale.sale_date < recent_boundary]

    def _remove_outliers(self, sales: list[_SalePoint]) -> list[_SalePoint]:
        if len(sales) < 4:
            return sales
        prices = [sale.price for sale in sales]
        center = median(prices)
        deviations = [abs(price - center) for price in prices]
        mad = median(deviations)
        if mad == 0:
            return sales
        filtered = [
            sale
            for sale in sales
            if abs(0.6745 * (sale.price - center) / mad) <= self.outlier_z_threshold
        ]
        return filtered or sales

    def _weighted_average(self, sales: list[_SalePoint], as_of: datetime) -> float | None:
        if not sales:
            return None
        weighted_sum = 0.0
        total_weight = 0.0
        for sale in sales:
            weight = self._recency_weight(sale=sale, as_of=as_of)
            weighted_sum += sale.price * weight
            total_weight += weight
        if total_weight == 0:
            return None
        return weighted_sum / total_weight

    def _weighted_median(self, sales: list[_SalePoint], as_of: datetime) -> float | None:
        if not sales:
            return None
        weighted_prices = sorted(
            ((sale.price, self._recency_weight(sale=sale, as_of=as_of)) for sale in sales),
            key=lambda row: row[0],
        )
        total_weight = sum(weight for _, weight in weighted_prices)
        if total_weight == 0:
            return None
        half_weight = total_weight / 2
        running_weight = 0.0
        for price, weight in weighted_prices:
            running_weight += weight
            if running_weight >= half_weight:
                return price
        return weighted_prices[-1][0]

    def _volatility(self, sales: list[_SalePoint]) -> float | None:
        prices = [sale.price for sale in sales]
        if len(prices) < 2:
            return None
        mean_price = sum(prices) / len(prices)
        if mean_price == 0:
            return None
        return pstdev(prices) / mean_price

    def _recency_weight(self, *, sale: _SalePoint, as_of: datetime) -> float:
        days_ago = max(0.0, (as_of - sale.sale_date).total_seconds() / 86400.0)
        return exp(-log(2) * days_ago / self.half_life_days)

    def _active_listing_count(self, *, listings: Iterable[MarketListing] | None, as_of: datetime) -> int:
        if listings is None:
            return 0
        count = 0
        for listing in listings:
            if not listing.is_active:
                continue
            if _to_utc(listing.listing_date) <= as_of:
                count += 1
        return count


def get_market_signal_capabilities() -> MarketSignalSummary:
    return MarketSignalSummary()


__all__ = [
    "MarketSignalSummary",
    "MarketMetrics",
    "MarketAnalysisEngine",
    "get_market_signal_capabilities",
]
