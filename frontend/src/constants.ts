import type { IncidentStatus, RiskLevel, Severity } from './types'

// Keys must cover every IncidentStatus value -- Record<> makes a missing
// entry a compile error rather than a silent blank badge.
export const STATUS_LABELS: Record<IncidentStatus, string> = {
  detected: 'Detected',
  triaged: 'Triaged',
  investigating: 'Investigating',
  diagnosed: 'Diagnosed',
  validating: 'Validating',
  awaiting_approval: 'Awaiting Approval',
  approved: 'Approved',
  rejected: 'Rejected',
  escalated: 'Escalated',
}

// awaiting_approval deliberately uses the accent color, not
// --status-attention (amber) -- amber is reserved for "high severity" now
// (see SEVERITY_COLORS below), so the two don't collide. The accent is the
// one color this app uses for "this needs you": the awaiting-approval
// badge, the section highlight, and the approve button all match.
export const STATUS_COLORS: Record<IncidentStatus, string> = {
  detected: 'var(--status-neutral)',
  triaged: 'var(--status-progress)',
  investigating: 'var(--status-progress)',
  diagnosed: 'var(--status-progress)',
  validating: 'var(--status-progress)',
  awaiting_approval: 'var(--accent-text)',
  approved: 'var(--status-good)',
  rejected: 'var(--status-bad)',
  escalated: 'var(--status-bad)',
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

export const SEVERITY_COLORS: Record<Severity, string> = {
  low: 'var(--status-neutral)',
  medium: 'var(--status-progress)',
  high: 'var(--status-attention)',
  critical: 'var(--status-bad)',
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  none: 'No risk',
  low: 'Low risk',
  medium: 'Medium risk',
  high: 'High risk',
}

export const RISK_COLORS: Record<RiskLevel, string> = {
  none: 'var(--status-neutral)',
  low: 'var(--status-good)',
  medium: 'var(--status-attention)',
  high: 'var(--status-bad)',
}

// The three list-page sections. Every IncidentStatus must appear in exactly
// one -- the Record<> below over SectionKey keys (not a loose array) is
// what makes "forgot to place a status" a compile error. Named SectionKey,
// not IncidentSection, to avoid colliding with the IncidentSection
// component.
export type SectionKey = 'awaiting_approval' | 'in_progress' | 'resolved'

const SECTION_BY_STATUS: Record<IncidentStatus, SectionKey> = {
  awaiting_approval: 'awaiting_approval',
  detected: 'in_progress',
  triaged: 'in_progress',
  investigating: 'in_progress',
  diagnosed: 'in_progress',
  validating: 'in_progress',
  approved: 'resolved',
  rejected: 'resolved',
  escalated: 'resolved',
}

export function sectionForStatus(status: IncidentStatus): SectionKey {
  return SECTION_BY_STATUS[status]
}

export const SECTION_TITLES: Record<SectionKey, string> = {
  awaiting_approval: 'Awaiting Your Approval',
  in_progress: 'In Progress',
  resolved: 'Resolved',
}

// Fixed, pipeline-ordered lists -- used to render the breakdown charts'
// rows in a stable order (including zero-count rows, so "nothing critical
// right now" is visible information, not a missing row).
export const ALL_STATUSES: readonly IncidentStatus[] = [
  'detected',
  'triaged',
  'investigating',
  'diagnosed',
  'validating',
  'awaiting_approval',
  'approved',
  'rejected',
  'escalated',
]

export const ALL_SEVERITIES: readonly Severity[] = ['critical', 'high', 'medium', 'low']
