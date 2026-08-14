from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SportBase(BaseModel):
    name: str = Field(max_length=100)


class SportCreate(SportBase):
    pass


class SportRead(ORMBaseModel, SportBase):
    id: int


class PlayerBase(BaseModel):
    sport_id: int
    name: str = Field(max_length=255)


class PlayerCreate(PlayerBase):
    pass


class PlayerRead(ORMBaseModel, PlayerBase):
    id: int


class GradingCompanyBase(BaseModel):
    name: str = Field(max_length=120)
    abbreviation: str | None = Field(default=None, max_length=20)


class GradingCompanyCreate(GradingCompanyBase):
    pass


class GradingCompanyRead(ORMBaseModel, GradingCompanyBase):
    id: int


class CardBase(BaseModel):
    sport_id: int
    player_id: int
    year: int
    manufacturer: str = Field(max_length=120)
    set_name: str = Field(max_length=255)
    card_number: str = Field(max_length=50)
    is_rookie: bool = False


class CardCreate(CardBase):
    pass


class CardRead(ORMBaseModel, CardBase):
    id: int


class CardVariantBase(BaseModel):
    card_id: int
    parallel: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=50)
    is_autograph: bool = False
    is_memorabilia: bool = False
    grading_company_id: int | None = None
    grade: str | None = Field(default=None, max_length=20)


class CardVariantCreate(CardVariantBase):
    pass


class CardVariantRead(ORMBaseModel, CardVariantBase):
    id: int


class HistoricalSaleBase(BaseModel):
    card_id: int
    sale_price: Decimal
    sale_date: datetime
    marketplace: str = Field(max_length=120)
    source: str = Field(max_length=120)
    currency: str = Field(default="USD", max_length=8)


class HistoricalSaleCreate(HistoricalSaleBase):
    pass


class HistoricalSaleRead(ORMBaseModel, HistoricalSaleBase):
    id: int


class MarketListingBase(BaseModel):
    card_id: int
    listing_price: Decimal
    marketplace: str = Field(max_length=120)
    listing_url: str
    listing_date: datetime
    is_active: bool = True
    currency: str = Field(default="USD", max_length=8)


class MarketListingCreate(MarketListingBase):
    pass


class MarketListingRead(ORMBaseModel, MarketListingBase):
    id: int


class MarketSnapshotBase(BaseModel):
    card_id: int
    snapshot_at: datetime
    average_price: Decimal | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    listing_count: int = 0
    marketplace: str | None = Field(default=None, max_length=120)
    currency: str = Field(default="USD", max_length=8)


class MarketSnapshotCreate(MarketSnapshotBase):
    pass


class MarketSnapshotRead(ORMBaseModel, MarketSnapshotBase):
    id: int


class PredictionBase(BaseModel):
    card_id: int
    prediction_date: datetime
    prediction_horizon_days: int
    current_price: Decimal
    predicted_direction: Literal["up", "down", "stable"]
    predicted_percentage_change: Decimal
    confidence: Decimal
    model_version: str = Field(max_length=120)


class PredictionCreate(PredictionBase):
    pass


class PredictionRead(ORMBaseModel, PredictionBase):
    id: int


class WatchlistBase(BaseModel):
    watcher_id: str = Field(max_length=120)
    card_id: int


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistRead(ORMBaseModel, WatchlistBase):
    id: int
    created_at: datetime
