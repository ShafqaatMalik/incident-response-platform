import { Badge } from './Badge'
import { SEVERITY_LABELS, SEVERITY_COLORS } from '../constants'
import type { Severity } from '../types'

export function SeverityBadge({ severity }: { severity: Severity | null }) {
  if (severity === null) {
    return <Badge label="Not yet triaged" color="var(--status-neutral)" />
  }
  return <Badge label={SEVERITY_LABELS[severity]} color={SEVERITY_COLORS[severity]} />
}
