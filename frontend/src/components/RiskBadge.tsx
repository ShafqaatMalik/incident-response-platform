import { Badge } from './Badge'
import { RISK_LABELS, RISK_COLORS } from '../constants'
import type { RiskLevel } from '../types'

export function RiskBadge({ risk }: { risk: RiskLevel | null }) {
  if (risk === null) {
    return null
  }
  return <Badge label={RISK_LABELS[risk]} color={RISK_COLORS[risk]} />
}
