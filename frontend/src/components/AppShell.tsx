import type { PropsWithChildren } from 'react'

export function AppShell({ children }: PropsWithChildren) {
  return (
    <main style={{ fontFamily: 'Arial, sans-serif', margin: '0 auto', maxWidth: 960, padding: '2rem' }}>
      <header>
        <p style={{ color: '#666', marginBottom: '0.5rem' }}>CardSignal AI</p>
        <h1 style={{ marginTop: 0 }}>Sports card market intelligence scaffold</h1>
      </header>
      {children}
    </main>
  )
}
