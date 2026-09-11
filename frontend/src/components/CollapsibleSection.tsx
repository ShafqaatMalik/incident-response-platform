import type { ReactNode } from 'react'
import styles from './CollapsibleSection.module.css'

interface CollapsibleSectionProps {
  title: string
  children: ReactNode
}

// Plain <details>/<summary> -- closed by default, no JS state needed, works
// without JavaScript at all, and is free keyboard/screen-reader accessible
// disclosure semantics rather than a hand-rolled toggle.
export function CollapsibleSection({ title, children }: CollapsibleSectionProps) {
  return (
    <details className={styles.details}>
      <summary className={styles.summary}>{title}</summary>
      <div className={styles.body}>{children}</div>
    </details>
  )
}
