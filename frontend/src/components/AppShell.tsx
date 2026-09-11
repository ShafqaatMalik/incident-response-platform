import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import styles from './AppShell.module.css'

interface AppShellProps {
  children: ReactNode
}

// Full-width top header bar, not a sidebar -- just the wordmark for now,
// no nav items, since there's only one real page today. Wraps both routes
// so the header is consistent everywhere; each page's own content renders
// below it exactly as it did directly in the body before.
export function AppShell({ children }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.wordmark}>
          Incident Response
        </Link>
      </header>
      <main>{children}</main>
    </div>
  )
}
