import type { CSSProperties } from 'react'
import styles from './Badge.module.css'

interface BadgeProps {
  label: string
  color: string
}

// Generic color-coded pill -- StatusBadge/SeverityBadge/RiskBadge are all
// this with different label/color lookup tables, so the actual markup and
// styling lives in one place.
export function Badge({ label, color }: BadgeProps) {
  const style = { '--badge-color': color } as CSSProperties
  return (
    <span className={styles.badge} style={style}>
      {label}
    </span>
  )
}
