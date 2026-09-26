// Row shapes follow the reporting API (GET /reports/...), so pages can switch from sample data to the API later.

export type Priority = 'P1' | 'P2' | 'P3'

export interface WorklistRow {
  complaint_id: string
  account_id: string
  category: string
  region: string
  priority: Priority
  classified_priority: Priority
  days_overdue: number
  breached_live: boolean
  domain: string
  routed_team: string | null
  lane: 'emergency' | 'review' | 'quick_lane' | 'standard' | null
  likely_cause: string | null
  next_action: string | null
}

export interface FlowRow {
  month: string
  opened: number
  closed: number
  net_change: number
  backlog_end_of_month: number
}

export interface BreakdownRow {
  region: string
  open_cases: number
  breached_cases: number
  at_risk_cases: number
  total_days_overdue: number
  share_of_backlog: number
}

export interface RootCauseRow {
  month: string
  region: string
  estimated_read_rate: number
  smart_meter_penetration: number
  billing_exceptions_per_1000: number
  complaints: number
  billing_metering_per_1000: number
}

export interface ClusterRow {
  region: string
  category: string
  open_cases: number
  breached_cases: number
  region_estimated_read_rate: number
  estimation_driven: boolean
}

export interface CaseRow {
  complaint_id: string
  date_opened: string
  status: 'Open' | 'Closed' | 'Closed - reopened'
  category: string
  region: string
  priority: Priority
  days_open: number
  breached_live: boolean
  routed_team: string | null
  resolution_action: string | null
}

export interface AccountHistoryRow {
  account_id: string
  complaint_id: string
  date_opened: string
  category: string
  status: string
  complaint_seq: number
  complaints_on_account: number
  days_since_previous: number | null
  is_repeat: boolean
}

export interface AgentResultRow {
  agent_id: string
  name: string
  classified: number
  fast_lane: number
  runs: number
  drafts_pending: number
  drafts_approved: number
}

export interface ClassificationSummaryRow {
  group_name: string
  classifications: number
  share_of_total: number
  avg_group_confidence: number
  data_fallbacks: number
}

export interface ProfileRow {
  category: string
  region: string
  source_system: string
  n: number
  avg_days: number
  info_only_share: number
  transfer_rate: number
  reopen_rate: number
  top_resolution: string
}
