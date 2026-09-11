import { Link } from 'react-router-dom'
import { IncidentCard } from './IncidentCard'
import type { SectionKey } from '../constants'
import type { Incident } from '../types'
import styles from './IncidentSection.module.css'

interface IncidentSectionProps {
  title: string
  incidents: Incident[]
  tone: SectionKey
  emptyMessage: string
  /** If set and there are more than `limit` incidents, only the first
   * `limit` render, plus a "View all" link to `viewAllHref`. Omit for an
   * uncapped view (e.g. the filtered single-section page). */
  limit?: number
  viewAllHref?: string
}

// One of the list page's three sections: a header (title + count, colored
// per `tone` -- see IncidentSection.module.css's [data-tone] rules) and
// either a card list or an empty-state message. The section itself is
// always shown, so the page's structure stays predictable even when a
// section has nothing in it.
export function IncidentSection({
  title,
  incidents,
  tone,
  emptyMessage,
  limit,
  viewAllHref,
}: IncidentSectionProps) {
  const capped = limit !== undefined && incidents.length > limit
  const visible = capped ? incidents.slice(0, limit) : incidents

  return (
    <section className={styles.section}>
      <div className={styles.header} data-tone={tone}>
        <h2 className={styles.title}>{title}</h2>
        <span className={styles.count}>{incidents.length}</span>
      </div>

      {incidents.length === 0 ? (
        <p className={styles.empty}>{emptyMessage}</p>
      ) : (
        <>
          <div className={styles.list}>
            {visible.map((incident) => (
              <IncidentCard key={incident.id} incident={incident} tone={tone} />
            ))}
          </div>
          {capped && viewAllHref && (
            <Link to={viewAllHref} className={styles.viewAll}>
              View all {incidents.length} →
            </Link>
          )}
        </>
      )}
    </section>
  )
}
