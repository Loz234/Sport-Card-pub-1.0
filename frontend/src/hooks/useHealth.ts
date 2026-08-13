import { useEffect, useState } from 'react'

import { fetchHealth } from '../services/api'
import type { HealthResponse } from '../types/system'

interface UseHealthState {
  data: HealthResponse | null
  loading: boolean
  error: string | null
}

export function useHealth(): UseHealthState {
  const [data, setData] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHealth()
      .then((payload) => {
        setData(payload)
        setError(null)
      })
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.message.includes('Failed to fetch')) {
          setError('Unable to reach the backend service.')
          return
        }
        setError('Unable to load backend status.')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  return { data, loading, error }
}
