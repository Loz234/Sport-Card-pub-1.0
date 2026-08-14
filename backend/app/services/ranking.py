from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.domain import Card, HistoricalSale, MarketListing, Player, Prediction, Sport


@dataclass(frozen=True)
class RankingQuery:
    sport: str | None = None
    min_confidence: float = 0.0
    min_sales_volume: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class RankedCard:
    card_name: str
    player: str
    sport: str
    current_estimated_price: float
    predicted_30_day_movement: float
    predicted_direction: str
    confidence: float
    data_quality: float
    model_version: str
    ranking_score: float


@dataclass(frozen=True)
class RankingPage:
    items: list[RankedCard]
    total: int
    page: int
    page_size: int
    data_quality_threshold: float


class MoversLosersRankingEngine:
    DATA_QUALITY_THRESHOLD = 0.5

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_movers(self, query: RankingQuery) -> RankingPage:
        return self._rank(direction="movers", query=query)

    def get_losers(self, query: RankingQuery) -> RankingPage:
        return self._rank(direction="losers", query=query)

    def _rank(self, *, direction: str, query: RankingQuery) -> RankingPage:
        rows = self._candidate_rows(query=query)
        ranked: list[RankedCard] = []

        for row in rows:
            predicted_change = float(row.predicted_percentage_change)
            if direction == "movers" and predicted_change <= 0:
                continue
            if direction == "losers" and predicted_change >= 0:
                continue

            sales_volume = int(row.sales_volume or 0)
            active_listings = int(row.active_listings or 0)
            confidence = float(row.confidence)

            sales_score = min(1.0, sales_volume / 12.0)
            liquidity_score = min(1.0, (sales_volume + active_listings) / 20.0)
            data_quality = round(self._data_quality_score(row=row, sales_score=sales_score, liquidity_score=liquidity_score), 4)
            if data_quality < self.DATA_QUALITY_THRESHOLD:
                continue

            model_reliability = self._model_reliability(model_version=str(row.model_version), confidence=confidence)
            ranking_score = abs(predicted_change) * (
                (0.35 * confidence)
                + (0.15 * sales_score)
                + (0.15 * liquidity_score)
                + (0.2 * data_quality)
                + (0.15 * model_reliability)
            )

            ranked.append(
                RankedCard(
                    card_name=self._card_name(
                        year=row.year,
                        manufacturer=row.manufacturer,
                        set_name=row.set_name,
                        card_number=row.card_number,
                    ),
                    player=str(row.player_name),
                    sport=str(row.sport_name),
                    current_estimated_price=float(row.current_price),
                    predicted_30_day_movement=round(predicted_change, 4),
                    predicted_direction=("UP" if predicted_change > 0 else "DOWN"),
                    confidence=round(confidence, 4),
                    data_quality=data_quality,
                    model_version=str(row.model_version),
                    ranking_score=ranking_score,
                )
            )

        ranked.sort(key=lambda card: card.ranking_score, reverse=True)

        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paged_items = ranked[start:end]

        return RankingPage(
            items=paged_items,
            total=len(ranked),
            page=query.page,
            page_size=query.page_size,
            data_quality_threshold=self.DATA_QUALITY_THRESHOLD,
        )

    def _candidate_rows(self, *, query: RankingQuery):
        now = datetime.now(UTC)
        sales_since = now - timedelta(days=30)

        latest_prediction = (
            select(
                Prediction.card_id.label("card_id"),
                Prediction.current_price.label("current_price"),
                Prediction.predicted_percentage_change.label("predicted_percentage_change"),
                Prediction.predicted_direction.label("predicted_direction"),
                Prediction.confidence.label("confidence"),
                Prediction.model_version.label("model_version"),
                func.row_number().over(
                    partition_by=Prediction.card_id,
                    order_by=Prediction.prediction_date.desc(),
                ).label("row_number"),
            )
            .where(Prediction.prediction_horizon_days == 30)
            .subquery()
        )

        sales_volume = (
            select(
                HistoricalSale.card_id.label("card_id"),
                func.count(HistoricalSale.id).label("sales_volume"),
            )
            .where(HistoricalSale.sale_date >= sales_since)
            .group_by(HistoricalSale.card_id)
            .subquery()
        )

        active_listings = (
            select(
                MarketListing.card_id.label("card_id"),
                func.count(MarketListing.id).label("active_listings"),
            )
            .where(and_(MarketListing.is_active.is_(True), MarketListing.listing_date <= now))
            .group_by(MarketListing.card_id)
            .subquery()
        )

        statement: Select[tuple] = (
            select(
                Card.year,
                Card.manufacturer,
                Card.set_name,
                Card.card_number,
                Player.name.label("player_name"),
                Sport.name.label("sport_name"),
                latest_prediction.c.current_price,
                latest_prediction.c.predicted_percentage_change,
                latest_prediction.c.predicted_direction,
                latest_prediction.c.confidence,
                latest_prediction.c.model_version,
                func.coalesce(sales_volume.c.sales_volume, 0).label("sales_volume"),
                func.coalesce(active_listings.c.active_listings, 0).label("active_listings"),
            )
            .join(latest_prediction, latest_prediction.c.card_id == Card.id)
            .join(Player, Player.id == Card.player_id)
            .join(Sport, Sport.id == Card.sport_id)
            .outerjoin(sales_volume, sales_volume.c.card_id == Card.id)
            .outerjoin(active_listings, active_listings.c.card_id == Card.id)
            .where(latest_prediction.c.row_number == 1)
            .where(latest_prediction.c.current_price > 0)
            .where(latest_prediction.c.confidence >= query.min_confidence)
            .where(func.coalesce(sales_volume.c.sales_volume, 0) >= query.min_sales_volume)
        )

        if query.sport:
            statement = statement.where(func.lower(Sport.name) == query.sport.lower())

        return self.db.execute(statement).all()

    def _data_quality_score(self, *, row, sales_score: float, liquidity_score: float) -> float:
        fields = [
            row.year,
            row.manufacturer,
            row.set_name,
            row.card_number,
            row.player_name,
            row.sport_name,
            row.current_price,
            row.predicted_percentage_change,
            row.predicted_direction,
            row.model_version,
        ]
        completeness = sum(1 for value in fields if value not in (None, "")) / len(fields)
        return (0.45 * sales_score) + (0.35 * liquidity_score) + (0.2 * completeness)

    def _model_reliability(self, *, model_version: str, confidence: float) -> float:
        version = model_version.lower()
        if version.startswith("xgb"):
            base = 0.9
        elif version.startswith("baseline"):
            base = 0.65
        else:
            base = 0.75
        return min(1.0, max(0.0, base * (0.65 + (0.35 * confidence))))

    def _card_name(self, *, year: int, manufacturer: str, set_name: str, card_number: str) -> str:
        core = f"{year} {manufacturer} {set_name}".strip()
        if card_number:
            return f"{core} #{card_number}"
        return core


__all__ = [
    "RankingQuery",
    "RankedCard",
    "RankingPage",
    "MoversLosersRankingEngine",
]
