import { Link } from 'react-router-dom'
import { SeverityBadge } from './SeverityBadge'
import { StatusBadge } from './StatusBadge'
import type { Incident } from '../types'
import type { SectionKey } from '../constants'
import styles from './IncidentCard.module.css'

interface IncidentCardProps {
  incident: Incident
  tone: SectionKey
}

function formatCreatedAt(iso: string): string {
  return new Date(iso).toLocaleString()
}

// One incident as a clickable card. `tone` (the section it's in) drives a
// left accent bar and a faint full-card background wash via `data-tone` --
// see IncidentCard.module.css. Deliberately NOT applied to the status/
// severity badges themselves: those keep their own fixed semantic colors
// (see constants.ts) so e.g. an escalated incident still reads as
// attention-worthy even inside the muted-green "Resolved" column. Cohesion
// lives at the card level, meaning lives at the badge level.
export function IncidentCard({ incident, tone }: IncidentCardProps) {
  return (
    <Link to={`/incidents/${incident.id}`} className={styles.card} data-tone={tone}>
      <div className={styles.badgeRow}>
        <StatusBadge status={incident.status} />
        <SeverityBadge severity={incident.severity} />
      </div>
      <p className={styles.trigger}>{incident.trigger}</p>
      <p className={styles.createdAt}>{formatCreatedAt(incident.created_at)}</p>
    </Link>
  )
}
