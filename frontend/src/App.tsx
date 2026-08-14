import { useEffect, useState } from 'react'

import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { CardDetailPage } from './pages/CardDetailPage'

function getCardIdFromHash(): number | null {
  const match = window.location.hash.match(/^#card\/(\d+)$/)
  if (!match) {
    return null
  }

  const value = Number(match[1])
  return Number.isFinite(value) ? value : null
}

function App() {
  const [selectedCardId, setSelectedCardId] = useState<number | null>(() => getCardIdFromHash())

  useEffect(() => {
    const handleHashChange = () => {
      setSelectedCardId(getCardIdFromHash())
    }

    window.addEventListener('hashchange', handleHashChange)
    return () => {
      window.removeEventListener('hashchange', handleHashChange)
    }
  }, [])

  function openCardDetail(cardId: number) {
    window.location.hash = `card/${cardId}`
  }

  function closeCardDetail() {
    window.location.hash = ''
  }

  return (
    <AppShell>
      {selectedCardId === null ? (
        <DashboardPage onSelectCard={openCardDetail} />
      ) : (
        <CardDetailPage cardId={selectedCardId} onBack={closeCardDetail} />
      )}
    </AppShell>
  )
}

export default App
