// Mirrors app/models/schemas.py's IncidentResponse / IncidentListResponse
// and app/models/incident.py's enums exactly -- keep these in sync with the
// backend by hand, there is no shared codegen between the two today.

export type IncidentStatus =
  | 'detected'
  | 'triaged'
  | 'investigating'
  | 'diagnosed'
  | 'validating'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'escalated'

export type Severity = 'low' | 'medium' | 'high' | 'critical'

export type Confidence = 'low' | 'medium' | 'high'

export type ActionType =
  | 'restart_service'
  | 'rollback_deployment'
  | 'scale_up'
  | 'disable_traffic'
  | 'no_action_needed'
  | 'manual_investigation_required'

export type RiskLevel = 'none' | 'low' | 'medium' | 'high'

export interface Incident {
  id: string
  created_at: string
  status: IncidentStatus
  trigger: string
  severity: Severity | null
  affected_service: string | null
  symptoms: string[] | null
  evidence: string[]
  escalation_reason: string | null
  error_patterns: string[] | null
  deployment_correlation: string | null
  service_health_summary: string | null
  investigation_confidence: Confidence | null
  root_cause: string | null
  alternative_explanations: string[] | null
  diagnosis_confidence: Confidence | null
  proposed_action_type: ActionType | null
  action_risk_level: RiskLevel | null
  action_justification: string | null
  action_detail: string | null
  approved_by: string | null
  approved_at: string | null
  rejected_by: string | null
  rejected_at: string | null
  rejection_reason: string | null
}

export interface IncidentListResponse {
  items: Incident[]
  total: number
  limit: number
  offset: number
  open_count: number
  awaiting_approval_count: number
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    request_id: string | null
  }
}
