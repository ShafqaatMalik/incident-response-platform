import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { describeError, getIncident } from '../api/client'
import { ApproveRejectPanel } from '../components/ApproveRejectPanel'
import { CollapsibleSection } from '../components/CollapsibleSection'
import { RiskBadge } from '../components/RiskBadge'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import type { Incident } from '../types'
import styles from './IncidentDetailPage.module.css'

function formatDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : ''
}

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [incident, setIncident] = useState<Incident | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const result = await getIncident(id)
      setIncident(result)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="page">
      <Link to="/" className={styles.backLink}>
        ← Back to incidents
      </Link>

      {error && (
        <div className={styles.errorBanner}>
          <span>{error}</span>
          <button type="button" onClick={load}>
            Retry
          </button>
        </div>
      )}

      {!error && loading && !incident && <p className={styles.muted}>Loading incident…</p>}

      {incident && (
        <>
          <div className={styles.titleRow}>
            <h1>Incident</h1>
            <StatusBadge status={incident.status} />
            <button type="button" onClick={load} className={styles.refreshButton}>
              Refresh
            </button>
          </div>

          <section className={styles.story}>
            <h3>What happened</h3>
            <p className={styles.trigger}>{incident.trigger}</p>

            <h3>What the system found</h3>
            <div className={styles.badgeRow}>
              <SeverityBadge severity={incident.severity} />
            </div>
            <p>
              {incident.root_cause ??
                incident.escalation_reason ??
                'Not yet diagnosed.'}
            </p>

            {incident.proposed_action_type && (
              <>
                <h3>What it wants to do</h3>
                <div className={styles.badgeRow}>
                  <RiskBadge risk={incident.action_risk_level} />
                </div>
                <p>{incident.action_detail}</p>
              </>
            )}

            {incident.status === 'approved' && (
              <p className={styles.decisionNote}>
                Approved by {incident.approved_by} at {formatDateTime(incident.approved_at)}
              </p>
            )}
            {incident.status === 'rejected' && (
              <p className={styles.decisionNote}>
                Rejected by {incident.rejected_by} at {formatDateTime(incident.rejected_at)}:{' '}
                {incident.rejection_reason}
              </p>
            )}
          </section>

          {incident.status === 'awaiting_approval' && (
            <ApproveRejectPanel incidentId={incident.id} onUpdated={setIncident} />
          )}

          <h2>More detail</h2>

          {incident.symptoms !== null && (
            <CollapsibleSection title="Triage">
              <dl>
                <dt>Affected service</dt>
                <dd>{incident.affected_service}</dd>
                <dt>Symptoms</dt>
                <dd>
                  <ul>
                    {incident.symptoms.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </dd>
                <dt>Evidence so far</dt>
                <dd>
                  <ul>
                    {incident.evidence.map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                </dd>
              </dl>
            </CollapsibleSection>
          )}

          {incident.error_patterns !== null && (
            <CollapsibleSection title="Investigation">
              <dl>
                <dt>Error patterns</dt>
                <dd>
                  <ul>
                    {incident.error_patterns.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                </dd>
                <dt>Deployment correlation</dt>
                <dd>{incident.deployment_correlation}</dd>
                <dt>Service health summary</dt>
                <dd>{incident.service_health_summary}</dd>
                <dt>Confidence</dt>
                <dd>{incident.investigation_confidence}</dd>
              </dl>
            </CollapsibleSection>
          )}

          {incident.alternative_explanations !== null && (
            <CollapsibleSection title="Diagnosis">
              <dl>
                <dt>Root cause</dt>
                <dd>{incident.root_cause}</dd>
                <dt>Alternative explanations considered</dt>
                <dd>
                  <ul>
                    {incident.alternative_explanations.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                </dd>
                <dt>Confidence</dt>
                <dd>{incident.diagnosis_confidence}</dd>
              </dl>
            </CollapsibleSection>
          )}

          {incident.action_justification !== null && (
            <CollapsibleSection title="Remediation">
              <dl>
                <dt>Proposed action</dt>
                <dd>{incident.proposed_action_type}</dd>
                <dt>Justification</dt>
                <dd>{incident.action_justification}</dd>
                <dt>Detail</dt>
                <dd>{incident.action_detail}</dd>
              </dl>
            </CollapsibleSection>
          )}
        </>
      )}
    </div>
  )
}
