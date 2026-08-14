export interface RankedCard {
  card_id: number
  card_name: string
  player: string
  sport: string
  current_estimated_price: number
  predicted_30_day_movement: number
  predicted_direction: string
  confidence: number
  data_quality: number
  model_version: string
}

export interface RankedCardsPageResponse {
  items: RankedCard[]
  total: number
  page: number
  page_size: number
  data_quality_threshold: number
}

export interface TrendingCard {
  card_id: number
  card_name: string
  player: string
  sport: string
  trending_score: number
  price_momentum: number | null
  sales_momentum: number | null
  supply_signal: number | null
  activity_signal: number | null
}

export interface TrendingCardsResponse {
  items: TrendingCard[]
}

export interface HistoricalPricePoint {
  timestamp: string
  price: number
}

export interface CardDetail {
  card_id: number
  card_name: string
  player: string
  sport: string
  set_name: string
  parallel: string | null
  grade: string | null
  current_estimated_market_value: number | null
  historical_market_data: {
    price_points: HistoricalPricePoint[]
    available_ranges: string[]
  }
  ai_prediction: {
    direction: string | null
    predicted_30_day_movement: number | null
    predicted_90_day_movement: number | null
    confidence: number | null
    market_momentum: number | null
    sales_volume: number
    sales_velocity: number
    trending_score: number | null
    data_quality: string
    disclaimer: string
  }
  explanation: {
    generated_from_validated_backend_data: boolean
    summary: string
    positive_signals: string[]
    risks: string[]
    why_model_may_be_wrong: string[]
    confidence: string
  }
}

export interface AddToWatchlistResponse {
  card_id: number
  watcher_id: string
  added: boolean
}
