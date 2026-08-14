from pydantic import BaseModel


class RankedCardResponse(BaseModel):
    card_id: int
    card_name: str
    player: str
    sport: str
    current_estimated_price: float
    predicted_30_day_movement: float
    predicted_direction: str
    confidence: float
    data_quality: float
    model_version: str


class RankedCardsPageResponse(BaseModel):
    items: list[RankedCardResponse]
    total: int
    page: int
    page_size: int
    data_quality_threshold: float
