from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import tanh
from statistics import mean, median

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import Card, HistoricalSale, MarketListing, MarketSnapshot


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class TrendingCard:
    card_name: str
    player: str
    sport: str
    trending_score: float
    price_momentum: float | None
    sales_momentum: float | None
    supply_signal: float | None
    activity_signal: float | None


class TrendingCardsEngine:
    RECENT_WINDOW_DAYS = 7
    BASELINE_WINDOW_DAYS = 28
    HISTORICAL_WINDOW_DAYS = 120
    MIN_RECENT_SALES = 2
    MIN_BASELINE_SALES = 4
    MIN_TOTAL_SALES = 8
    MIN_SIGNALS = 3
    TRENDING_SCORE_THRESHOLD = 45.0

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_trending(self) -> list[TrendingCard]:
        as_of = datetime.now(UTC)
        cards = self._candidate_cards(as_of=as_of)
        ranked = [card for candidate in cards if (card := self._build_trending_card(card=candidate, as_of=as_of)) is not None]
        ranked.sort(key=lambda item: item.trending_score, reverse=True)
        return ranked

    def _candidate_cards(self, *, as_of: datetime) -> list[Card]:
        sales_since = as_of - timedelta(days=self.HISTORICAL_WINDOW_DAYS)
        statement = (
            select(Card)
            .options(
                selectinload(Card.player),
                selectinload(Card.sport),
                selectinload(Card.historical_sales),
                selectinload(Card.market_listings),
                selectinload(Card.market_snapshots),
            )
            .where(
                exists(
                    select(HistoricalSale.id).where(
                        HistoricalSale.card_id == Card.id,
                        HistoricalSale.sale_date >= sales_since,
                    )
                )
            )
        )
        return self.db.execute(statement).scalars().unique().all()

    def _build_trending_card(self, *, card: Card, as_of: datetime) -> TrendingCard | None:
        recent_boundary = as_of - timedelta(days=self.RECENT_WINDOW_DAYS)
        baseline_boundary = recent_boundary - timedelta(days=self.BASELINE_WINDOW_DAYS)
        historical_boundary = as_of - timedelta(days=self.HISTORICAL_WINDOW_DAYS)

        sales = [
            sale
            for sale in card.historical_sales
            if historical_boundary <= _to_utc(sale.sale_date) <= as_of and float(sale.sale_price) > 0
        ]
        if len(sales) < self.MIN_TOTAL_SALES:
            return None

        recent_sales = [sale for sale in sales if _to_utc(sale.sale_date) >= recent_boundary]
        baseline_sales = [sale for sale in sales if baseline_boundary <= _to_utc(sale.sale_date) < recent_boundary]
        older_sales = [sale for sale in sales if historical_boundary <= _to_utc(sale.sale_date) < baseline_boundary]

        if len(recent_sales) < self.MIN_RECENT_SALES or len(baseline_sales) < self.MIN_BASELINE_SALES:
            return None

        price_momentum = self._price_momentum(recent_sales=recent_sales, baseline_sales=baseline_sales)
        sales_momentum = self._sales_momentum(recent_sales=recent_sales, baseline_sales=baseline_sales)
        supply_signal = self._supply_signal(
            snapshots=card.market_snapshots,
            listings=card.market_listings,
            as_of=as_of,
            recent_boundary=recent_boundary,
            baseline_boundary=baseline_boundary,
        )
        activity_signal = self._activity_signal(recent_sales=recent_sales, baseline_sales=baseline_sales, older_sales=older_sales)

        signal_values = [value for value in [price_momentum, sales_momentum, supply_signal, activity_signal] if value is not None]
        if len(signal_values) < self.MIN_SIGNALS:
            return None

        trending_score = self._trending_score(
            recent_sales=recent_sales,
            baseline_sales=baseline_sales,
            older_sales=older_sales,
            price_momentum=price_momentum,
            sales_momentum=sales_momentum,
            supply_signal=supply_signal,
            activity_signal=activity_signal,
        )
        if trending_score < self.TRENDING_SCORE_THRESHOLD:
            return None

        player_name = card.player.name if card.player is not None else ""
        sport_name = card.sport.name if card.sport is not None else ""

        return TrendingCard(
            card_name=self._card_name(
                year=card.year,
                manufacturer=card.manufacturer,
                set_name=card.set_name,
                card_number=card.card_number,
            ),
            player=player_name,
            sport=sport_name,
            trending_score=trending_score,
            price_momentum=price_momentum,
            sales_momentum=sales_momentum,
            supply_signal=supply_signal,
            activity_signal=activity_signal,
        )

    def _price_momentum(self, *, recent_sales: list[HistoricalSale], baseline_sales: list[HistoricalSale]) -> float | None:
        baseline_average = self._average_price(baseline_sales)
        recent_average = self._average_price(recent_sales)
        if baseline_average in (None, 0.0) or recent_average is None:
            return None
        return round((recent_average - baseline_average) / baseline_average, 4)

    def _sales_momentum(self, *, recent_sales: list[HistoricalSale], baseline_sales: list[HistoricalSale]) -> float | None:
        baseline_rate = len(baseline_sales) / float(self.BASELINE_WINDOW_DAYS)
        if baseline_rate == 0:
            return None
        recent_rate = len(recent_sales) / float(self.RECENT_WINDOW_DAYS)
        return round((recent_rate / baseline_rate) - 1.0, 4)

    def _supply_signal(
        self,
        *,
        snapshots: list[MarketSnapshot],
        listings: list[MarketListing],
        as_of: datetime,
        recent_boundary: datetime,
        baseline_boundary: datetime,
    ) -> float | None:
        baseline_snapshots = [
            snapshot
            for snapshot in snapshots
            if baseline_boundary <= _to_utc(snapshot.snapshot_at) < recent_boundary
        ]
        if not baseline_snapshots:
            return None

        baseline_listing_count = median(snapshot.listing_count for snapshot in baseline_snapshots)
        if baseline_listing_count <= 0:
            return None

        current_active = self._current_active_listings(listings=listings, as_of=as_of)
        if current_active is None:
            recent_snapshots = [snapshot for snapshot in snapshots if recent_boundary <= _to_utc(snapshot.snapshot_at) <= as_of]
            if not recent_snapshots:
                return None
            current_active = recent_snapshots[-1].listing_count

        return round((baseline_listing_count - current_active) / baseline_listing_count, 4)

    def _activity_signal(
        self,
        *,
        recent_sales: list[HistoricalSale],
        baseline_sales: list[HistoricalSale],
        older_sales: list[HistoricalSale],
    ) -> float | None:
        recent_rate = len(recent_sales) / float(self.RECENT_WINDOW_DAYS)
        baseline_rate = len(baseline_sales) / float(self.BASELINE_WINDOW_DAYS)
        older_days = max(1, self.HISTORICAL_WINDOW_DAYS - self.BASELINE_WINDOW_DAYS - self.RECENT_WINDOW_DAYS)

        normal_rates = [rate for rate in [baseline_rate, (len(older_sales) / float(older_days)) if older_sales else None] if rate not in (None, 0.0)]
        if not normal_rates:
            return None
        normal_rate = mean(normal_rates)
        if normal_rate == 0:
            return None
        return round((recent_rate / normal_rate) - 1.0, 4)

    def _trending_score(
        self,
        *,
        recent_sales: list[HistoricalSale],
        baseline_sales: list[HistoricalSale],
        older_sales: list[HistoricalSale],
        price_momentum: float | None,
        sales_momentum: float | None,
        supply_signal: float | None,
        activity_signal: float | None,
    ) -> float:
        weighted_components: list[tuple[float, float]] = []

        if price_momentum is not None:
            weighted_components.append((0.35, abs(self._normalize(price_momentum, scale=0.20))))
            price_acceleration = self._price_acceleration(recent_sales=recent_sales, baseline_sales=baseline_sales)
            if price_acceleration is not None:
                weighted_components.append((0.15, abs(self._normalize(price_acceleration, scale=0.20))))
        if sales_momentum is not None:
            weighted_components.append((0.2, max(0.0, self._normalize(sales_momentum, scale=1.0))))
            sales_velocity_ratio = self._sales_velocity_ratio(recent_sales=recent_sales, older_sales=older_sales)
            if sales_velocity_ratio is not None:
                weighted_components.append((0.1, max(0.0, self._normalize(sales_velocity_ratio, scale=1.0))))
        if supply_signal is not None:
            weighted_components.append((0.1, abs(self._normalize(supply_signal, scale=0.35))))
        if activity_signal is not None:
            weighted_components.append((0.1, max(0.0, self._normalize(activity_signal, scale=1.0))))

        total_weight = sum(weight for weight, _ in weighted_components)
        if total_weight == 0:
            return 0.0

        score = 100.0 * sum(weight * value for weight, value in weighted_components) / total_weight
        return round(score, 2)

    def _price_acceleration(self, *, recent_sales: list[HistoricalSale], baseline_sales: list[HistoricalSale]) -> float | None:
        recent_average = self._average_price(recent_sales)
        baseline_average = self._average_price(baseline_sales)
        if recent_average is None or baseline_average in (None, 0.0):
            return None

        baseline_midpoint = len(baseline_sales) // 2
        earlier_baseline = baseline_sales[:baseline_midpoint]
        later_baseline = baseline_sales[baseline_midpoint:]
        earlier_average = self._average_price(earlier_baseline)
        later_average = self._average_price(later_baseline)
        if earlier_average in (None, 0.0) or later_average is None:
            return None

        prior_momentum = (later_average - earlier_average) / earlier_average
        current_momentum = (recent_average - baseline_average) / baseline_average
        return current_momentum - prior_momentum

    def _sales_velocity_ratio(self, *, recent_sales: list[HistoricalSale], older_sales: list[HistoricalSale]) -> float | None:
        older_days = max(1, self.HISTORICAL_WINDOW_DAYS - self.BASELINE_WINDOW_DAYS - self.RECENT_WINDOW_DAYS)
        older_rate = len(older_sales) / float(older_days)
        if older_rate == 0:
            return None
        recent_rate = len(recent_sales) / float(self.RECENT_WINDOW_DAYS)
        return (recent_rate / older_rate) - 1.0

    def _average_price(self, sales: list[HistoricalSale]) -> float | None:
        if not sales:
            return None
        return mean(float(sale.sale_price) for sale in sales)

    def _current_active_listings(self, *, listings: list[MarketListing], as_of: datetime) -> int | None:
        active_listings = [
            listing
            for listing in listings
            if listing.is_active and _to_utc(listing.listing_date) <= as_of
        ]
        if not active_listings:
            return None
        return len(active_listings)

    def _normalize(self, value: float, *, scale: float) -> float:
        if scale <= 0:
            return 0.0
        return tanh(value / scale)

    def _card_name(self, *, year: int, manufacturer: str, set_name: str, card_number: str) -> str:
        core = f"{year} {manufacturer} {set_name}".strip()
        if card_number:
            return f"{core} #{card_number}"
        return core


__all__ = ["TrendingCard", "TrendingCardsEngine"]
