import { Badge } from './Badge'
import { STATUS_COLORS, STATUS_LABELS } from '../constants'
import type { IncidentStatus } from '../types'

export function StatusBadge({ status }: { status: IncidentStatus }) {
  return <Badge label={STATUS_LABELS[status]} color={STATUS_COLORS[status]} />
}
