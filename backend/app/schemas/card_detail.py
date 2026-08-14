from pydantic import BaseModel


class HistoricalPricePointResponse(BaseModel):
    timestamp: str
    price: float


class HistoricalMarketDataResponse(BaseModel):
    price_points: list[HistoricalPricePointResponse]
    available_ranges: list[str]


class AIPredictionResponse(BaseModel):
    direction: str | None
    predicted_30_day_movement: float | None
    predicted_90_day_movement: float | None
    confidence: float | None
    market_momentum: float | None
    sales_volume: int
    sales_velocity: float
    trending_score: float | None
    disclaimer: str


class PredictionExplanationResponse(BaseModel):
    generated_from_validated_backend_data: bool
    reasons: list[str]


class CardDetailResponse(BaseModel):
    card_id: int
    card_name: str
    player: str
    sport: str
    set_name: str
    parallel: str | None
    grade: str | None
    current_estimated_market_value: float | None
    historical_market_data: HistoricalMarketDataResponse
    ai_prediction: AIPredictionResponse
    explanation: PredictionExplanationResponse


class AddToWatchlistRequest(BaseModel):
    watcher_id: str


class AddToWatchlistResponse(BaseModel):
    card_id: int
    watcher_id: str
    added: bool
