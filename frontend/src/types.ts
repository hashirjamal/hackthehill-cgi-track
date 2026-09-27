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
  date_closed: string | null
  status: string
  category: string
  region: string
  channel: string
  priority: Priority
  resolution_action: string | null
  days_to_close: number | null
  reopened: boolean
  transferred_between_systems: boolean
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
  runs_failed: number
  drafts: number
  drafts_pending: number
  drafts_approved: number
  drafts_edited: number
  drafts_rejected: number
  drafts_sent: number
}

/** One group of the classification results. The grouping column is named by `group_by`. */
export interface ClassificationSummaryRow {
  classifications: number
  share_of_total: number
  avg_group_confidence: number | null
  data_fallbacks: number
  group_match_rate: number | null
  [column: string]: string | number | boolean | null
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
  breach_rate: number
  top_resolution: string
  avg_bill_correction: number | null
}

export interface CaseFlag {
  name: string
  source: string
  effect: string
  probability: number | null
  reason: string
}

export interface CaseClassification {
  classification_id: number
  classifier_version: string
  created_at: string
  emergency: boolean
  group_name: string | null
  group_confidence: number | null
  group_source: 'laya' | 'data' | null
  laya_group: string | null
  subcategory: string | null
  subcategory_source: string | null
  low_confidence: boolean
  priority: Priority
  base_priority: Priority
  base_priority_source: string
  routed_team: string
  lane: 'emergency' | 'review' | 'quick_lane' | 'standard'
  likely_cause: string | null
  flags: CaseFlag[]
}

export interface MeterMonth {
  month: string
  estimated_read_rate: number
  smart_meter_penetration: number
  billing_exceptions_raised: number
  billing_exceptions_per_1000: number
}

export interface ResolutionShare {
  resolution_action: string
  cases: number
  share: number
}

export interface CaseProfile {
  n: number
  avg_days: number | null
  info_only_share: number | null
  transfer_rate: number | null
  reopen_rate: number | null
  breach_rate: number | null
}

export interface AccountCase {
  complaint_id: string
  date_opened: string
  status: string
  category: string
  region: string
  priority: Priority
  resolution_action: string | null
  days_to_close: number | null
  reopened: boolean
  complaint_seq: number
  is_repeat: boolean
  days_since_previous: number | null
}

/** GET /reports/cases/{id}: everything known about one complaint. */
export interface CaseContext {
  case: CaseRow
  classification: CaseClassification | null
  region_meter: MeterMonth[]
  profile: (CaseProfile & { top_resolution: string }) | null
  category_profile: CaseProfile | null
  resolution_mix: ResolutionShare[]
  account_complaints_total: number
  account_history: AccountCase[]
  drafts: { draft_id: number; run_id: number | null; status: string; body: string; created_at: string }[]
  action_items: CaseActionItem[]
  /** source systems the agent checked, for the latest Get context and Generate draft runs, by run_id. */
  systems_checked: Record<string, SystemCall[]>
  /** Whether each of those runs used the local AI or the no-AI rules. */
  run_modes: Record<string, 'ai' | 'rules'>
}

/** One request the agent made to a source system. */
export interface SystemCall {
  system: 'helix' | 'aurora' | 'casetrack' | 'callcentre' | 'connect'
  system_name: string
  request: string
  raw: string | null
  summary: string | null
}

export interface CaseActionItem {
  action_id: number
  run_id: number | null
  action_type: string
  description: string
  rationale: string | null
  rank: number
  status: string
}

/** POST /complaints/{id}/context and /draft. A run can fail without an HTTP error: check status. */
export interface AgentRunResult {
  run_id: number
  status: 'succeeded' | 'failed'
  /** A note, e.g. why the no-AI rules were used instead of the AI. */
  error: string | null
  mode: 'ai' | 'rules'
  systems_checked: SystemCall[]
}
export interface ContextResult extends AgentRunResult {
  action_items: { action_id: number; action_type: string; description: string; rationale: string | null; rank: number }[]
}
export interface DraftResult extends AgentRunResult {
  draft_id: number | null
  body: string | null
}
