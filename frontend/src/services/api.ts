import type { RankedCardsPageResponse, TrendingCardsResponse } from '../types/market'
import type { HealthResponse } from '../types/system'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health')
}

export async function fetchTopMovers(): Promise<RankedCardsPageResponse> {
  return request<RankedCardsPageResponse>('/api/v1/movers?page=1&page_size=5')
}

export async function fetchTopLosers(): Promise<RankedCardsPageResponse> {
  return request<RankedCardsPageResponse>('/api/v1/losers?page=1&page_size=5')
}

export async function fetchTrendingNow(): Promise<TrendingCardsResponse> {
  return request<TrendingCardsResponse>('/api/v1/trending')
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return (await response.json()) as T
}
