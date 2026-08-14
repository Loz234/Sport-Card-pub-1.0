from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.trending import TrendingCardResponse, TrendingCardsResponse
from app.services.trending import TrendingCardsEngine

router = APIRouter()


@router.get("/trending", response_model=TrendingCardsResponse)
def get_trending(db: Session = Depends(get_db)) -> TrendingCardsResponse:
    engine = TrendingCardsEngine(db)
    items = [
        TrendingCardResponse(
            card_id=item.card_id,
            card_name=item.card_name,
            player=item.player,
            sport=item.sport,
            trending_score=item.trending_score,
            price_momentum=item.price_momentum,
            sales_momentum=item.sales_momentum,
            supply_signal=item.supply_signal,
            activity_signal=item.activity_signal,
        )
        for item in engine.get_trending()
    ]
    return TrendingCardsResponse(items=items)
