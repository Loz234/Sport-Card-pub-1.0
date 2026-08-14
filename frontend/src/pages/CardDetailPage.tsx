import { useEffect, useMemo, useState } from 'react'

import { addToWatchlist, fetchCardDetail } from '../services/api'
import type { CardDetail, HistoricalPricePoint } from '../types/market'

interface CardDetailPageProps {
  cardId: number
  onBack: () => void
}

type RangeOption = '7d' | '30d' | '90d' | '1y'

interface DetailState {
  loading: boolean
  error: string | null
  item: CardDetail | null
}

const initialState: DetailState = {
  loading: true,
  error: null,
  item: null,
}

const rangeDays: Record<RangeOption, number> = {
  '7d': 7,
  '30d': 30,
  '90d': 90,
  '1y': 365,
}

function formatCurrency(value: number | null): string {
  if (value === null) {
    return 'N/A'
  }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return 'N/A'
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatConfidence(value: number | null): string {
  if (value === null) {
    return 'N/A'
  }
  return `${(value * 100).toFixed(2)}%`
}

function metricClass(value: number | null): string {
  if (value === null) {
    return 'neutral'
  }
  if (value > 0) {
    return 'up'
  }
  if (value < 0) {
    return 'down'
  }
  return 'neutral'
}

export function CardDetailPage({ cardId, onBack }: CardDetailPageProps) {
  const [detail, setDetail] = useState<DetailState>(initialState)
  const [selectedRange, setSelectedRange] = useState<RangeOption>('30d')
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null)
  const [watchlistPending, setWatchlistPending] = useState(false)

  useEffect(() => {
    let active = true
    setDetail(initialState)
    setWatchlistMessage(null)

    void fetchCardDetail(cardId)
      .then((item) => {
        if (!active) {
          return
        }
        setDetail({ loading: false, error: null, item })
      })
      .catch(() => {
        if (!active) {
          return
        }
        setDetail({ loading: false, error: 'Unable to load card detail.', item: null })
      })

    return () => {
      active = false
    }
  }, [cardId])

  const filteredPoints = useMemo(() => {
    if (!detail.item) {
      return []
    }
    return filterPoints(detail.item.historical_market_data.price_points, selectedRange)
  }, [detail.item, selectedRange])

  async function handleWatchlist() {
    setWatchlistPending(true)
    setWatchlistMessage(null)
    try {
      const response = await addToWatchlist(cardId)
      setWatchlistMessage(response.added ? 'Added to watchlist.' : 'Already in watchlist.')
    } catch {
      setWatchlistMessage('Unable to add this card to the watchlist.')
    } finally {
      setWatchlistPending(false)
    }
  }

  return (
    <section className="detail-page">
      <div className="detail-toolbar">
        <button type="button" className="secondary-button" onClick={onBack}>
          ← Back to dashboard
        </button>
        <button type="button" className="primary-button" onClick={handleWatchlist} disabled={watchlistPending || detail.loading}>
          {watchlistPending ? 'Adding…' : 'Add to Watchlist'}
        </button>
      </div>

      {detail.loading && <p className="state">Loading card detail…</p>}
      {!detail.loading && detail.error && <p className="state error">{detail.error}</p>}

      {!detail.loading && !detail.error && detail.item && (
        <>
          <section className="section detail-summary">
            <div>
              <p className="eyebrow">Card Detail</p>
              <h2>{detail.item.card_name}</h2>
              <div className="detail-meta-grid">
                <DetailMeta label="Player" value={detail.item.player} />
                <DetailMeta label="Sport" value={detail.item.sport} />
                <DetailMeta label="Set" value={detail.item.set_name} />
                <DetailMeta label="Parallel" value={detail.item.parallel ?? 'N/A'} />
                <DetailMeta label="Grade" value={detail.item.grade ?? 'N/A'} />
              </div>
            </div>
            <div className="value-card">
              <span>Current estimated market value</span>
              <strong>{formatCurrency(detail.item.current_estimated_market_value)}</strong>
              <p>Calculated from validated backend market data.</p>
              {watchlistMessage && <p className="watchlist-message">{watchlistMessage}</p>}
            </div>
          </section>

          <section className="section historical-panel">
            <div className="section-heading-row">
              <div>
                <p className="eyebrow">Historical market data</p>
                <h2>Historical price chart</h2>
              </div>
              <div className="range-tabs" role="tablist" aria-label="Historical price ranges">
                {detail.item.historical_market_data.available_ranges.map((range) => (
                  <button
                    key={range}
                    type="button"
                    role="tab"
                    className={range === selectedRange ? 'range-tab active' : 'range-tab'}
                    aria-selected={range === selectedRange}
                    onClick={() => {
                      setSelectedRange(range as RangeOption)
                    }}
                  >
                    {range === '1y' ? '1 year' : range.replace('d', ' days')}
                  </button>
                ))}
              </div>
            </div>
            <PriceChart points={filteredPoints} />
            <p className="supporting-copy">This chart only shows validated historical sale prices captured by the backend.</p>
          </section>

          <section className="section prediction-panel">
            <div className="section-heading-row stacked-on-mobile">
              <div>
                <p className="eyebrow">AI predictions</p>
                <h2>Model outlook</h2>
              </div>
              <p className="prediction-disclaimer">{detail.item.ai_prediction.disclaimer}</p>
            </div>
            <div className="metrics-grid">
              <MetricCard label="AI prediction" value={detail.item.ai_prediction.direction ?? 'N/A'} toneClass={metricClass(directionToNumber(detail.item.ai_prediction.direction))} />
              <MetricCard label="Predicted 30-day movement" value={formatPercent(detail.item.ai_prediction.predicted_30_day_movement)} toneClass={metricClass(detail.item.ai_prediction.predicted_30_day_movement)} />
              <MetricCard label="Predicted 90-day movement" value={formatPercent(detail.item.ai_prediction.predicted_90_day_movement)} toneClass={metricClass(detail.item.ai_prediction.predicted_90_day_movement)} />
              <MetricCard label="AI confidence" value={formatConfidence(detail.item.ai_prediction.confidence)} />
              <MetricCard label="Market momentum" value={formatPercent(detail.item.ai_prediction.market_momentum)} toneClass={metricClass(detail.item.ai_prediction.market_momentum)} />
              <MetricCard label="Sales volume" value={detail.item.ai_prediction.sales_volume.toString()} />
              <MetricCard label="Sales velocity" value={`${detail.item.ai_prediction.sales_velocity.toFixed(2)} / day`} />
              <MetricCard label="Trending score" value={detail.item.ai_prediction.trending_score === null ? 'N/A' : detail.item.ai_prediction.trending_score.toFixed(2)} />
            </div>
          </section>

          <section className="section explanation-panel">
            <p className="eyebrow">Why is AI predicting this?</p>
            <h2>Explanation</h2>
            <p className="supporting-copy">Generated from validated backend data only. No unsupported statistics are shown.</p>
            <ul className="explanation-list">
              {detail.item.explanation.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </section>
        </>
      )}
    </section>
  )
}

function filterPoints(points: HistoricalPricePoint[], range: RangeOption): HistoricalPricePoint[] {
  if (points.length === 0) {
    return []
  }

  const latestTimestamp = new Date(points[points.length - 1].timestamp).getTime()
  const cutoff = latestTimestamp - rangeDays[range] * 24 * 60 * 60 * 1000

  return points.filter((point) => new Date(point.timestamp).getTime() >= cutoff)
}

function directionToNumber(direction: string | null): number | null {
  if (direction === 'UP') {
    return 1
  }
  if (direction === 'DOWN') {
    return -1
  }
  if (direction === 'STABLE') {
    return 0
  }
  return null
}

interface DetailMetaProps {
  label: string
  value: string
}

function DetailMeta({ label, value }: DetailMetaProps) {
  return (
    <div className="detail-meta-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string
  toneClass?: string
}

function MetricCard({ label, value, toneClass }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong className={toneClass}>{value}</strong>
    </article>
  )
}

interface PriceChartProps {
  points: HistoricalPricePoint[]
}

function PriceChart({ points }: PriceChartProps) {
  if (points.length === 0) {
    return <p className="state">No validated historical sales are available for this range.</p>
  }

  if (points.length === 1) {
    return (
      <div className="chart-card single-point-chart">
        <strong>{formatCurrency(points[0].price)}</strong>
        <span>{new Date(points[0].timestamp).toLocaleDateString()}</span>
      </div>
    )
  }

  const width = 720
  const height = 260
  const padding = 24
  const prices = points.map((point) => point.price)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceRange = Math.max(maxPrice - minPrice, 1)
  const maxIndex = Math.max(points.length - 1, 1)

  const chartPoints = points
    .map((point, index) => {
      const x = padding + ((width - padding * 2) * index) / maxIndex
      const y = height - padding - ((point.price - minPrice) / priceRange) * (height - padding * 2)
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className="chart-card">
      <svg viewBox={`0 0 ${width} ${height}`} className="price-chart" role="img" aria-label="Historical price chart">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="chart-axis" />
        <polyline fill="none" stroke="currentColor" strokeWidth="3" points={chartPoints} className="chart-line" />
      </svg>
      <div className="chart-summary-row">
        <span>Low: {formatCurrency(minPrice)}</span>
        <span>High: {formatCurrency(maxPrice)}</span>
      </div>
    </div>
  )
}
