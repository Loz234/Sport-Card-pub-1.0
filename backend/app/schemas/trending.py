from pydantic import BaseModel


class TrendingCardResponse(BaseModel):
    card_id: int
    card_name: str
    player: str
    sport: str
    trending_score: float
    price_momentum: float | None
    sales_momentum: float | None
    supply_signal: float | None
    activity_signal: float | None


class TrendingCardsResponse(BaseModel):
    items: list[TrendingCardResponse]
