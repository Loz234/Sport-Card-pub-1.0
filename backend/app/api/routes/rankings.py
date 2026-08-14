from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ranking import RankedCardsPageResponse
from app.services.ranking import MoversLosersRankingEngine, RankingPage, RankingQuery

router = APIRouter()


def _to_response(page_result: RankingPage) -> RankedCardsPageResponse:
    return RankedCardsPageResponse(
        items=[
            {
                "card_id": item.card_id,
                "card_name": item.card_name,
                "player": item.player,
                "sport": item.sport,
                "current_estimated_price": item.current_estimated_price,
                "predicted_30_day_movement": item.predicted_30_day_movement,
                "predicted_direction": item.predicted_direction,
                "confidence": item.confidence,
                "data_quality": item.data_quality,
                "model_version": item.model_version,
            }
            for item in page_result.items
        ],
        total=page_result.total,
        page=page_result.page,
        page_size=page_result.page_size,
        data_quality_threshold=page_result.data_quality_threshold,
    )


@router.get("/movers", response_model=RankedCardsPageResponse)
def get_movers(
    sport: str | None = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    min_sales_volume: int = Query(default=0, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> RankedCardsPageResponse:
    engine = MoversLosersRankingEngine(db)
    query = RankingQuery(
        sport=sport,
        min_confidence=min_confidence,
        min_sales_volume=min_sales_volume,
        page=page,
        page_size=page_size,
    )
    page_result = engine.get_movers(query)
    return _to_response(page_result)


@router.get("/losers", response_model=RankedCardsPageResponse)
def get_losers(
    sport: str | None = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    min_sales_volume: int = Query(default=0, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> RankedCardsPageResponse:
    engine = MoversLosersRankingEngine(db)
    query = RankingQuery(
        sport=sport,
        min_confidence=min_confidence,
        min_sales_volume=min_sales_volume,
        page=page,
        page_size=page_size,
    )
    page_result = engine.get_losers(query)
    return _to_response(page_result)
