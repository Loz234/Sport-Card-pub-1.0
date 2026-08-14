import { type ReactNode, useEffect, useMemo, useState } from 'react'

import { fetchTopLosers, fetchTopMovers, fetchTrendingNow } from '../services/api'
import type { RankedCard, TrendingCard } from '../types/market'

interface SectionState<T> {
  loading: boolean
  error: string | null
  items: T[]
}

const initialSectionState = <T,>(): SectionState<T> => ({
  loading: true,
  error: null,
  items: [],
})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return 'N/A'
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function matchesSearch(searchTerm: string, ...fields: string[]): boolean {
  const term = searchTerm.trim().toLowerCase()
  if (!term) {
    return true
  }
  return fields.some((value) => value.toLowerCase().includes(term))
}

function directionLabel(direction: string): string {
  const normalized = direction.toLowerCase()
  if (normalized === 'up') {
    return 'UP ▲'
  }
  if (normalized === 'down') {
    return 'DOWN ▼'
  }
  return 'STABLE ■'
}

function directionClass(direction: string): string {
  const normalized = direction.toLowerCase()
  if (normalized === 'up') {
    return 'up'
  }
  if (normalized === 'down') {
    return 'down'
  }
  return 'neutral'
}

interface DashboardPageProps {
  onSelectCard: (cardId: number) => void
}

export function DashboardPage({ onSelectCard }: DashboardPageProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [movers, setMovers] = useState<SectionState<RankedCard>>(initialSectionState)
  const [losers, setLosers] = useState<SectionState<RankedCard>>(initialSectionState)
  const [trending, setTrending] = useState<SectionState<TrendingCard>>(initialSectionState)

  useEffect(() => {
    let active = true

    void fetchTopMovers()
      .then((response) => {
        if (!active) {
          return
        }
        setMovers({ loading: false, error: null, items: response.items })
      })
      .catch(() => {
        if (!active) {
          return
        }
        setMovers({ loading: false, error: 'Unable to load top movers.', items: [] })
      })

    void fetchTopLosers()
      .then((response) => {
        if (!active) {
          return
        }
        setLosers({ loading: false, error: null, items: response.items })
      })
      .catch(() => {
        if (!active) {
          return
        }
        setLosers({ loading: false, error: 'Unable to load top losers.', items: [] })
      })

    void fetchTrendingNow()
      .then((response) => {
        if (!active) {
          return
        }
        setTrending({ loading: false, error: null, items: response.items.slice(0, 5) })
      })
      .catch(() => {
        if (!active) {
          return
        }
        setTrending({ loading: false, error: 'Unable to load trending cards.', items: [] })
      })

    return () => {
      active = false
    }
  }, [])

  const filteredMovers = useMemo(
    () => movers.items.filter((item) => matchesSearch(searchTerm, item.card_name, item.player)),
    [movers.items, searchTerm],
  )
  const filteredLosers = useMemo(
    () => losers.items.filter((item) => matchesSearch(searchTerm, item.card_name, item.player)),
    [losers.items, searchTerm],
  )
  const filteredTrending = useMemo(
    () => trending.items.filter((item) => matchesSearch(searchTerm, item.card_name, item.player)),
    [trending.items, searchTerm],
  )

  return (
    <section className="dashboard">
      <div id="search" className="search-wrap">
        <label htmlFor="search-input" className="search-label">
          Search
        </label>
        <input
          id="search-input"
          type="search"
          value={searchTerm}
          onChange={(event) => {
            setSearchTerm(event.target.value)
          }}
          placeholder="Search cards or players"
          className="search-input"
        />
      </div>

      <Section id="movers" title="TOP MOVERS" loading={movers.loading} error={movers.error} isEmpty={filteredMovers.length === 0}>
        <div className="card-grid">
          {filteredMovers.map((item) => (
            <article className="data-card" key={`mover-${item.card_id}`}>
              <h3>{item.card_name}</h3>
              <p>Player: {item.player}</p>
              <p>Current price: {formatCurrency(item.current_estimated_price)}</p>
              <p>Predicted 30-day movement: {formatPercent(item.predicted_30_day_movement)}</p>
              <p>Confidence: {formatPercent(item.confidence * 100)}</p>
              <p className={directionClass(item.predicted_direction)}>{directionLabel(item.predicted_direction)}</p>
              <button type="button" className="card-action" onClick={() => onSelectCard(item.card_id)}>
                View details
              </button>
            </article>
          ))}
        </div>
      </Section>

      <Section id="losers" title="TOP LOSERS" loading={losers.loading} error={losers.error} isEmpty={filteredLosers.length === 0}>
        <div className="card-grid">
          {filteredLosers.map((item) => (
            <article className="data-card" key={`loser-${item.card_id}`}>
              <h3>{item.card_name}</h3>
              <p>Player: {item.player}</p>
              <p>Current price: {formatCurrency(item.current_estimated_price)}</p>
              <p>Predicted 30-day movement: {formatPercent(item.predicted_30_day_movement)}</p>
              <p>Confidence: {formatPercent(item.confidence * 100)}</p>
              <p className={directionClass(item.predicted_direction)}>{directionLabel(item.predicted_direction)}</p>
              <button type="button" className="card-action" onClick={() => onSelectCard(item.card_id)}>
                View details
              </button>
            </article>
          ))}
        </div>
      </Section>

      <Section
        id="trending"
        title="TRENDING NOW"
        loading={trending.loading}
        error={trending.error}
        isEmpty={filteredTrending.length === 0}
      >
        <div className="card-grid">
          {filteredTrending.map((item) => (
            <article className="data-card" key={`trending-${item.card_id}`}>
              <h3>{item.card_name}</h3>
              <p>Trending score: {item.trending_score.toFixed(2)}</p>
              <p>Price momentum: {formatPercent(item.price_momentum)}</p>
              <p>Sales momentum: {formatPercent(item.sales_momentum)}</p>
              <button type="button" className="card-action" onClick={() => onSelectCard(item.card_id)}>
                View details
              </button>
            </article>
          ))}
        </div>
      </Section>

      <section id="watchlist" className="section">
        <h2>WATCHLIST</h2>
        <p className="state">Watchlist data is not available yet.</p>
      </section>
    </section>
  )
}

interface SectionProps {
  id?: string
  title: string
  loading: boolean
  error: string | null
  isEmpty: boolean
  children: ReactNode
}

function Section({ id, title, loading, error, isEmpty, children }: SectionProps) {
  return (
    <section id={id} className="section">
      <h2>{title}</h2>
      {loading && <p className="state">Loading…</p>}
      {!loading && error && <p className="state error">{error}</p>}
      {!loading && !error && isEmpty && <p className="state">No cards found.</p>}
      {!loading && !error && !isEmpty && children}
    </section>
  )
}
