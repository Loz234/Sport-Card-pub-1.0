from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.card_detail import AddToWatchlistRequest, AddToWatchlistResponse, CardDetailResponse
from app.services.card_detail import CardDetailService

router = APIRouter()


@router.get("/cards/{card_id}", response_model=CardDetailResponse)
def get_card_detail(card_id: int, db: Session = Depends(get_db)) -> CardDetailResponse:
    return CardDetailService(db).get_card_detail(card_id)


@router.post("/cards/{card_id}/watchlist", response_model=AddToWatchlistResponse)
def add_to_watchlist(
    card_id: int,
    payload: AddToWatchlistRequest,
    db: Session = Depends(get_db),
) -> AddToWatchlistResponse:
    watchlist, added = CardDetailService(db).add_to_watchlist(card_id=card_id, watcher_id=payload.watcher_id)
    return AddToWatchlistResponse(card_id=watchlist.card_id, watcher_id=watchlist.watcher_id, added=added)
