import { useHealth } from '../hooks/useHealth'

export function DashboardPage() {
  const { data, loading, error } = useHealth()

  return (
    <section>
      <p>
        This frontend is intentionally limited to project scaffolding and backend connectivity checks.
      </p>
      {loading && <p>Checking backend status…</p>}
      {error && <p style={{ color: '#b00020' }}>Backend unavailable: {error}</p>}
      {data && (
        <div>
          <h2>Backend status</h2>
          <ul>
            <li>API: {data.api.status}</li>
            <li>Database: {data.database.status}</li>
            <li>Ingestion: {data.ingestion.status}</li>
            <li>Market analysis: {data.market_analysis.status}</li>
            <li>Machine learning: {data.machine_learning.status}</li>
            <li>AI explanation: {data.ai_explanation.status}</li>
          </ul>
        </div>
      )}
    </section>
  )
}
