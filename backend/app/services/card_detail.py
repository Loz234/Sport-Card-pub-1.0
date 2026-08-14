from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import Card, CardVariant, Prediction, Watchlist
from app.schemas.card_detail import (
    AIPredictionResponse,
    CardDetailResponse,
    HistoricalMarketDataResponse,
    HistoricalPricePointResponse,
    PredictionExplanationResponse,
)
from app.services.market_analysis import MarketAnalysisEngine
from app.services.trending import TrendingCardsEngine
from app.services.utils import build_card_name


_DISCLAIMER = (
    "AI predictions are estimates derived from historical market data and model outputs. "
    "They are not guaranteed future returns or financial advice."
)


@dataclass(frozen=True)
class _PredictionSummary:
    direction: str | None
    movement_30d: float | None
    movement_90d: float | None
    confidence: float | None
    current_price: float | None


class CardDetailService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.market_analysis = MarketAnalysisEngine()
        self.trending_engine = TrendingCardsEngine(db)

    def get_card_detail(self, card_id: int) -> CardDetailResponse:
        card = self._load_card(card_id)
        as_of = self._analysis_as_of(card)
        prediction_summary = self._prediction_summary(card)
        metrics = self.market_analysis.calculate_metrics(
            sales=card.historical_sales,
            listings=card.market_listings,
            as_of=as_of,
        )
        explanation = self._build_explanation(prediction_summary=prediction_summary, metrics=metrics)

        return CardDetailResponse(
            card_id=card.id,
            card_name=build_card_name(
                year=card.year,
                manufacturer=card.manufacturer,
                set_name=card.set_name,
                card_number=card.card_number,
            ),
            player=card.player.name if card.player is not None else "Unknown",
            sport=card.sport.name if card.sport is not None else "Unknown",
            set_name=card.set_name,
            parallel=self._parallel(card),
            grade=self._grade(card),
            current_estimated_market_value=self._current_estimated_market_value(card=card, prediction_summary=prediction_summary),
            historical_market_data=HistoricalMarketDataResponse(
                price_points=self._historical_price_points(card),
                available_ranges=["7d", "30d", "90d", "1y"],
            ),
            ai_prediction=AIPredictionResponse(
                direction=prediction_summary.direction,
                predicted_30_day_movement=prediction_summary.movement_30d,
                predicted_90_day_movement=prediction_summary.movement_90d,
                confidence=prediction_summary.confidence,
                market_momentum=round(metrics.price_change * 100, 2) if metrics.price_change is not None else None,
                sales_volume=metrics.sales_volume,
                sales_velocity=round(metrics.sales_velocity, 2),
                trending_score=self._trending_score(card),
                disclaimer=_DISCLAIMER,
            ),
            explanation=PredictionExplanationResponse(
                generated_from_validated_backend_data=True,
                reasons=explanation,
            ),
        )

    def add_to_watchlist(self, *, card_id: int, watcher_id: str) -> tuple[Watchlist, bool]:
        card = self._load_card(card_id)
        existing = self.db.execute(
            select(Watchlist).where(Watchlist.card_id == card.id, Watchlist.watcher_id == watcher_id)
        ).scalar_one_or_none()
        if existing is not None:
            return existing, False

        watchlist = Watchlist(card_id=card.id, watcher_id=watcher_id)
        self.db.add(watchlist)
        self.db.commit()
        self.db.refresh(watchlist)
        return watchlist, True

    def _load_card(self, card_id: int) -> Card:
        statement = (
            select(Card)
            .options(
                selectinload(Card.player),
                selectinload(Card.sport),
                selectinload(Card.variants).selectinload(CardVariant.grading_company),
                selectinload(Card.historical_sales),
                selectinload(Card.market_listings),
                selectinload(Card.market_snapshots),
                selectinload(Card.predictions),
            )
            .where(Card.id == card_id)
        )
        card = self.db.execute(statement).scalar_one_or_none()
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found.")
        return card

    def _prediction_summary(self, card: Card) -> _PredictionSummary:
        prediction_30d = self._latest_prediction(card.predictions, horizon_days=30)
        prediction_90d = self._latest_prediction(card.predictions, horizon_days=90)
        direction = None
        confidence = None
        current_price = None

        if prediction_30d is not None:
            direction = str(prediction_30d.predicted_direction).upper()
            confidence = round(float(prediction_30d.confidence), 4)
            current_price = round(float(prediction_30d.current_price), 2)
        elif prediction_90d is not None:
            direction = str(prediction_90d.predicted_direction).upper()
            confidence = round(float(prediction_90d.confidence), 4)
            current_price = round(float(prediction_90d.current_price), 2)

        return _PredictionSummary(
            direction=direction,
            movement_30d=round(float(prediction_30d.predicted_percentage_change), 2) if prediction_30d is not None else None,
            movement_90d=round(float(prediction_90d.predicted_percentage_change), 2) if prediction_90d is not None else None,
            confidence=confidence,
            current_price=current_price,
        )

    def _latest_prediction(self, predictions: list[Prediction], *, horizon_days: int) -> Prediction | None:
        filtered = [prediction for prediction in predictions if prediction.prediction_horizon_days == horizon_days]
        if not filtered:
            return None
        return max(filtered, key=lambda prediction: prediction.prediction_date)

    def _parallel(self, card: Card) -> str | None:
        if not card.variants:
            return "Base"
        primary = card.variants[0]
        return primary.parallel or "Base"

    def _grade(self, card: Card) -> str | None:
        if not card.variants:
            return "Ungraded"
        primary = card.variants[0]
        if primary.grade and primary.grading_company is not None and primary.grading_company.abbreviation:
            return f"{primary.grading_company.abbreviation} {primary.grade}"
        if primary.grade:
            return primary.grade
        return "Ungraded"

    def _current_estimated_market_value(self, *, card: Card, prediction_summary: _PredictionSummary) -> float | None:
        if prediction_summary.current_price is not None:
            return prediction_summary.current_price
        recent_snapshots = sorted(card.market_snapshots, key=lambda snapshot: snapshot.snapshot_at, reverse=True)
        if recent_snapshots and recent_snapshots[0].average_price is not None:
            return round(float(recent_snapshots[0].average_price), 2)
        recent_sales = sorted(card.historical_sales, key=lambda sale: sale.sale_date, reverse=True)
        if recent_sales:
            return round(float(recent_sales[0].sale_price), 2)
        return None

    def _historical_price_points(self, card: Card) -> list[HistoricalPricePointResponse]:
        cutoff = datetime.now(UTC) - timedelta(days=365)
        filtered_sales = [
            sale for sale in sorted(card.historical_sales, key=lambda item: item.sale_date)
            if self._to_utc(sale.sale_date) >= cutoff and float(sale.sale_price) > 0
        ]
        return [
            HistoricalPricePointResponse(
                timestamp=self._to_utc(sale.sale_date).isoformat(),
                price=round(float(sale.sale_price), 2),
            )
            for sale in filtered_sales
        ]

    def _trending_score(self, card: Card) -> float | None:
        trending_card = self.trending_engine._build_trending_card(card=card, as_of=datetime.now(UTC))
        if trending_card is None:
            return None
        return trending_card.trending_score

    def _build_explanation(self, *, prediction_summary: _PredictionSummary, metrics) -> list[str]:
        reasons: list[str] = []

        if prediction_summary.movement_30d is not None and prediction_summary.direction is not None:
            reasons.append(
                f"The latest validated 30-day model output points {prediction_summary.direction} with an expected move of {prediction_summary.movement_30d:+.2f}%."
            )
        if prediction_summary.movement_90d is not None:
            reasons.append(
                f"The validated 90-day model output projects {prediction_summary.movement_90d:+.2f}% from the current estimate."
            )
        if metrics.median_price_7d is not None and metrics.median_price_30d is not None:
            reasons.append(
                f"Recent historical sales show a 7-day weighted median of ${metrics.median_price_7d:.2f} versus a 30-day weighted median of ${metrics.median_price_30d:.2f}."
            )
        if metrics.price_change is not None:
            reasons.append(
                f"Validated market momentum is {metrics.price_change * 100:+.2f}% based on recent sales versus the prior baseline window."
            )
        reasons.append(
            f"The backend has {metrics.sales_volume} validated sales in the last 30 days, which is a sales velocity of {metrics.sales_velocity:.2f} sales per day."
        )

        return reasons[:4] if len(reasons) > 4 else reasons

    def _analysis_as_of(self, card: Card) -> datetime:
        timestamps: list[datetime] = []
        timestamps.extend(self._to_utc(sale.sale_date) for sale in card.historical_sales)
        timestamps.extend(self._to_utc(listing.listing_date) for listing in card.market_listings)
        timestamps.extend(self._to_utc(snapshot.snapshot_at) for snapshot in card.market_snapshots)
        timestamps.extend(self._to_utc(prediction.prediction_date) for prediction in card.predictions)
        if not timestamps:
            return datetime.now(UTC)
        return max(timestamps)

    def _to_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


__all__ = ["CardDetailService"]
