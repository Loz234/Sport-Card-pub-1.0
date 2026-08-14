export interface RankedCard {
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
