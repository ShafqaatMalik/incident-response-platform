import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { describeError, listAllIncidents } from '../api/client'
import { BreakdownChart, type BreakdownRow } from '../components/BreakdownChart'
import { IncidentSection } from '../components/IncidentSection'
import {
  ALL_SEVERITIES,
  ALL_STATUSES,
  SECTION_TITLES,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
  STATUS_COLORS,
  STATUS_LABELS,
  sectionForStatus,
  type SectionKey,
} from '../constants'
import type { Incident } from '../types'
import styles from './IncidentListPage.module.css'

const POLL_INTERVAL_MS = 15_000
const SECTION_PREVIEW_LIMIT = 5

const SECTION_EMPTY_MESSAGES: Record<SectionKey, string> = {
  awaiting_approval: 'Nothing needs your approval right now.',
  in_progress: 'No incidents in this state.',
  resolved: 'No incidents in this state.',
}

function isSectionKey(value: string | null): value is SectionKey {
  return value === 'awaiting_approval' || value === 'in_progress' || value === 'resolved'
}

export function IncidentListPage() {
  const [incidents, setIncidents] = useState<Incident[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const pollRef = useRef<number | null>(null)
  const [searchParams] = useSearchParams()

  const load = useCallback(async () => {
    try {
      const result = await listAllIncidents()
      setIncidents(result)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()

    function tick() {
      if (document.visibilityState === 'visible') {
        load()
      }
    }
    pollRef.current = window.setInterval(tick, POLL_INTERVAL_MS)
    return () => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current)
      }
    }
  }, [load])

  const grouped = useMemo(() => {
    const awaiting: Incident[] = []
    const inProgress: Incident[] = []
    const resolved: Incident[] = []
    for (const incident of incidents ?? []) {
      const section = sectionForStatus(incident.status)
      if (section === 'awaiting_approval') awaiting.push(incident)
      else if (section === 'in_progress') inProgress.push(incident)
      else resolved.push(incident)
    }
    return { awaiting_approval: awaiting, in_progress: inProgress, resolved }
  }, [incidents])

  const severityRows: BreakdownRow[] = useMemo(
    () =>
      ALL_SEVERITIES.map((severity) => ({
        key: severity,
        label: SEVERITY_LABELS[severity],
        count: (incidents ?? []).filter((i) => i.severity === severity).length,
        color: SEVERITY_COLORS[severity],
      })),
    [incidents],
  )

  const statusRows: BreakdownRow[] = useMemo(
    () =>
      ALL_STATUSES.map((status) => ({
        key: status,
        label: STATUS_LABELS[status],
        count: (incidents ?? []).filter((i) => i.status === status).length,
        color: STATUS_COLORS[status],
      })),
    [incidents],
  )

  const filterParam = searchParams.get('section')
  const activeSection = isSectionKey(filterParam) ? filterParam : null

  return (
    <div className="page">
      <div className={styles.header}>
        <h1>Incidents</h1>
        <button type="button" onClick={load} disabled={loading} className={styles.refreshButton}>
          {loading ? 'Refreshing…' : 'Refresh now'}
        </button>
      </div>

      {error && (
        <div className={styles.errorBanner}>
          <span>{error}</span>
          <button type="button" onClick={load}>
            Retry
          </button>
        </div>
      )}

      {!error && loading && !incidents && <p className={styles.muted}>Loading incidents…</p>}

      {incidents && activeSection && (
        <>
          <Link to="/" className={styles.backLink}>
            ← Back to overview
          </Link>
          <IncidentSection
            title={SECTION_TITLES[activeSection]}
            incidents={grouped[activeSection]}
            tone={activeSection}
            emptyMessage={SECTION_EMPTY_MESSAGES[activeSection]}
          />
        </>
      )}

      {incidents && !activeSection && (
        <>
          <div className={styles.summaryRow}>
            <BreakdownChart title="By Severity" rows={severityRows} />
            <BreakdownChart title="By Status" rows={statusRows} />
          </div>

          <div className={styles.sectionsRow}>
            <IncidentSection
              title={SECTION_TITLES.awaiting_approval}
              incidents={grouped.awaiting_approval}
              tone="awaiting_approval"
              emptyMessage={SECTION_EMPTY_MESSAGES.awaiting_approval}
              limit={SECTION_PREVIEW_LIMIT}
              viewAllHref="?section=awaiting_approval"
            />
            <IncidentSection
              title={SECTION_TITLES.in_progress}
              incidents={grouped.in_progress}
              tone="in_progress"
              emptyMessage={SECTION_EMPTY_MESSAGES.in_progress}
              limit={SECTION_PREVIEW_LIMIT}
              viewAllHref="?section=in_progress"
            />
            <IncidentSection
              title={SECTION_TITLES.resolved}
              incidents={grouped.resolved}
              tone="resolved"
              emptyMessage={SECTION_EMPTY_MESSAGES.resolved}
              limit={SECTION_PREVIEW_LIMIT}
              viewAllHref="?section=resolved"
            />
          </div>
        </>
      )}
    </div>
  )
}
