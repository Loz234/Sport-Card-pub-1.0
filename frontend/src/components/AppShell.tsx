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
            <li>
              <a href="#movers">MOVERS</a>
            </li>
            <li>
              <a href="#losers">LOSERS</a>
            </li>
            <li>
              <a href="#trending">TRENDING</a>
            </li>
            <li>
              <a href="#search">SEARCH</a>
            </li>
            <li>
              <a href="#watchlist">WATCHLIST</a>
            </li>
          </ul>
        </nav>
      </header>
      {children}
    </main>
  )
}
