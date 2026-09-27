// Row shapes follow the reporting API (GET /reports/...), so pages can switch from sample data to the API later.

export type Priority = 'P1' | 'P2' | 'P3'

export interface WorklistRow {
  complaint_id: string
  account_id: string
  date_opened: string
  channel: string
  category: string
  priority: Priority
  region: string
  source_system: string
  sla_days: number
  days_open: number
  days_overdue: number
  breached_live: boolean
  domain: string
  classification_id: number | null
  group_name: string | null
  subcategory: string | null
  classified_priority: Priority
  base_priority: Priority | null
  base_priority_source: string | null
  routed_team: string | null
  lane: 'emergency' | 'review' | 'quick_lane' | 'standard' | null
  likely_cause: string | null
  low_confidence: boolean | null
  region_estimated_read_rate: number | null
  open_actions: number
  next_action: string | null
}

export interface FlowRow {
  month: string
  opened: number
  closed: number
  net_change: number
  backlog_end_of_month: number
  avg_days_to_close: number | null
  breach_rate_closed: number | null
}

/** One group of the open backlog. The grouping column (region, category ...) is named by `group_by`. */
export interface BreakdownRow {
  open_cases: number
  breached_cases: number
  at_risk_cases: number
  total_days_overdue: number
  avg_days_open: number
  share_of_backlog: number
  [column: string]: string | number | boolean | null
}

export interface RootCauseRow {
  month: string
  region: string
  accounts: number
  estimated_read_rate: number
  smart_meter_penetration: number
  billing_exceptions_raised: number
  billing_exceptions_per_1000: number
  complaints: number
  billing_metering_complaints: number
  billing_metering_per_1000: number
  billing_metering_share: number | null
}

export interface ClusterRow {
  region: string
  category: string
  open_cases: number
  breached_cases: number
  avg_days_open: number
  share_of_region_backlog: number
  region_estimated_read_rate: number | null
  region_smart_meter_penetration: number | null
  region_billing_exceptions_per_1000: number | null
  estimation_prone: boolean
  estimation_driven: boolean
}

export interface CaseRow {
  complaint_id: string
  account_id: string
  date_opened: string
  date_closed: string | null
  status: 'Open' | 'Closed' | 'Closed - reopened'
  channel: string
  category: string
  priority: Priority
  region: string
  source_system: string
  transferred_between_systems: boolean
  sla_days: number
  days_to_close: number | null
  reopened: boolean
  resolution_action: string | null
  resolvable_by_information_only: boolean | null
  bill_correction_value: number | null
  domain: string
  days_open: number
  days_overdue: number
  breached_live: boolean
  age_band: string
  classification_id: number | null
  group_name: string | null
  subcategory: string | null
  classified_priority: Priority
  routed_team: string | null
  lane: 'emergency' | 'review' | 'quick_lane' | 'standard' | null
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
