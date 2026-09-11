import { useState } from 'react'
import { approveIncident, describeError, rejectIncident } from '../api/client'
import type { Incident } from '../types'
import styles from './ApproveRejectPanel.module.css'

const REVIEWER_NAME_KEY = 'irp.reviewerName'

interface ApproveRejectPanelProps {
  incidentId: string
  onUpdated: (incident: Incident) => void
}

// Only ever rendered by IncidentDetailPage when status === "awaiting_approval".
export function ApproveRejectPanel({ incidentId, onUpdated }: ApproveRejectPanelProps) {
  const [reviewerName, setReviewerName] = useState(
    () => localStorage.getItem(REVIEWER_NAME_KEY) ?? '',
  )
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [submitting, setSubmitting] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)

  function updateReviewerName(value: string) {
    setReviewerName(value)
    localStorage.setItem(REVIEWER_NAME_KEY, value)
  }

  async function handleApprove() {
    setError(null)
    setSubmitting('approve')
    try {
      const updated = await approveIncident(incidentId, reviewerName)
      onUpdated(updated)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSubmitting(null)
    }
  }

  async function handleReject() {
    setError(null)
    setSubmitting('reject')
    try {
      const updated = await rejectIncident(incidentId, reviewerName, rejectionReason)
      onUpdated(updated)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSubmitting(null)
    }
  }

  const busy = submitting !== null
  const canSubmit = reviewerName.trim().length > 0

  return (
    <div className={styles.panel}>
      <label className={styles.nameField}>
        Your name
        <input
          type="text"
          value={reviewerName}
          onChange={(e) => updateReviewerName(e.target.value)}
          placeholder="e.g. jordan"
          disabled={busy}
        />
      </label>

      {!showRejectForm ? (
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.approve}
            onClick={handleApprove}
            disabled={busy || !canSubmit}
          >
            {submitting === 'approve' ? 'Approving…' : 'Approve'}
          </button>
          <button
            type="button"
            className={styles.reject}
            onClick={() => setShowRejectForm(true)}
            disabled={busy}
          >
            Reject
          </button>
        </div>
      ) : (
        <div className={styles.rejectForm}>
          <label className={styles.reasonField}>
            Rejection reason
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              rows={3}
              disabled={busy}
              placeholder="Why isn't this safe to run right now?"
            />
          </label>
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.reject}
              onClick={handleReject}
              disabled={busy || !canSubmit || rejectionReason.trim().length === 0}
            >
              {submitting === 'reject' ? 'Rejecting…' : 'Confirm reject'}
            </button>
            <button
              type="button"
              className={styles.cancel}
              onClick={() => setShowRejectForm(false)}
              disabled={busy}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}
