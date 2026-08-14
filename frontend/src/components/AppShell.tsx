import type { PropsWithChildren } from 'react'

export function AppShell({ children }: PropsWithChildren) {
  return (
    <main className="app-shell">
      <header className="hero">
        <p className="brand">CardSignal AI</p>
        <h1>Predict the next sports card market movers.</h1>
        <p className="subheading">AI-powered predictions based on historical sales and market activity.</p>
        <nav aria-label="Primary">
          <ul className="nav-list">
            <li>MOVERS</li>
            <li>LOSERS</li>
            <li>TRENDING</li>
            <li>SEARCH</li>
            <li>WATCHLIST</li>
          </ul>
        </nav>
      </header>
      {children}
    </main>
  )
}
