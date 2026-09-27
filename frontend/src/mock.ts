// Sample data for the first build. Shapes match the reporting API, so each page can switch to a fetch later.
import type {
  AccountHistoryRow,
  AgentResultRow,
  CaseRow,
  ClassificationSummaryRow,
  ClusterRow,
  ProfileRow,
  RootCauseRow,
} from './types'

export { CATEGORIES, CHANNELS, LANES, PRIORITIES, REGIONS, TEAMS } from './constants'

export const rootCause: RootCauseRow[] = [
  { month: '2026-09', region: 'Barrowdale', estimated_read_rate: 0.62, smart_meter_penetration: 0, billing_exceptions_per_1000: 25.4, complaints: 176, billing_metering_per_1000: 0.44 },
  { month: '2026-09', region: 'Dunmoor', estimated_read_rate: 0.615, smart_meter_penetration: 0, billing_exceptions_per_1000: 25.2, complaints: 189, billing_metering_per_1000: 0.71 },
  { month: '2026-09', region: 'Fenwick', estimated_read_rate: 0.26, smart_meter_penetration: 0.81, billing_exceptions_per_1000: 10.7, complaints: 206, billing_metering_per_1000: 0.53 },
  { month: '2026-09', region: 'Calderfield', estimated_read_rate: 0.21, smart_meter_penetration: 0.81, billing_exceptions_per_1000: 8.8, complaints: 188, billing_metering_per_1000: 0.32 },
  { month: '2026-09', region: 'Ashford', estimated_read_rate: 0.25, smart_meter_penetration: 0.81, billing_exceptions_per_1000: 10.3, complaints: 201, billing_metering_per_1000: 0.28 },
  { month: '2026-09', region: 'Eastmarch', estimated_read_rate: 0.18, smart_meter_penetration: 0.81, billing_exceptions_per_1000: 7.4, complaints: 193, billing_metering_per_1000: 0.36 },
  { month: '2026-08', region: 'Barrowdale', estimated_read_rate: 0.63, smart_meter_penetration: 0, billing_exceptions_per_1000: 25.6, complaints: 171, billing_metering_per_1000: 0.42 },
  { month: '2026-08', region: 'Dunmoor', estimated_read_rate: 0.6, smart_meter_penetration: 0, billing_exceptions_per_1000: 24.9, complaints: 184, billing_metering_per_1000: 0.69 },
]

export const clusters: ClusterRow[] = [
  { region: 'Barrowdale', category: 'Billing - estimated read', open_cases: 80, breached_cases: 39, region_estimated_read_rate: 0.62, estimation_driven: true },
  { region: 'Dunmoor', category: 'Billing - estimated read', open_cases: 64, breached_cases: 28, region_estimated_read_rate: 0.615, estimation_driven: true },
  { region: 'Barrowdale', category: 'Metering - no read taken', open_cases: 46, breached_cases: 24, region_estimated_read_rate: 0.62, estimation_driven: true },
  { region: 'Dunmoor', category: 'Metering - no read taken', open_cases: 38, breached_cases: 19, region_estimated_read_rate: 0.615, estimation_driven: true },
  { region: 'Fenwick', category: 'Billing - disputed amount', open_cases: 96, breached_cases: 52, region_estimated_read_rate: 0.26, estimation_driven: false },
  { region: 'Calderfield', category: 'Billing - disputed amount', open_cases: 91, breached_cases: 49, region_estimated_read_rate: 0.21, estimation_driven: false },
]

export const cases: CaseRow[] = [
  { complaint_id: 'NW-124358', date_opened: '2026-09-17', status: 'Open', category: 'Supply - interruption', region: 'Fenwick', priority: 'P1', days_open: 13, breached_live: true, routed_team: 'Network operations', resolution_action: null },
  { complaint_id: 'NW-120404', date_opened: '2026-06-16', status: 'Open', category: 'Billing - estimated read', region: 'Barrowdale', priority: 'P3', days_open: 106, breached_live: true, routed_team: 'Metering team', resolution_action: null },
  { complaint_id: 'NW-100003', date_opened: '2024-10-01', status: 'Closed - reopened', category: 'Billing - disputed amount', region: 'Ashford', priority: 'P2', days_open: 15, breached_live: true, routed_team: null, resolution_action: 'Bill corrected and re-issued' },
  { complaint_id: 'NW-100002', date_opened: '2024-10-01', status: 'Closed', category: 'Billing - disputed amount', region: 'Ashford', priority: 'P2', days_open: 6, breached_live: false, routed_team: null, resolution_action: 'Bill corrected and re-issued' },
  { complaint_id: 'NW-100001', date_opened: '2024-10-01', status: 'Closed', category: 'Billing - disputed amount', region: 'Ashford', priority: 'P3', days_open: 29, breached_live: true, routed_team: null, resolution_action: 'Refund or credit applied' },
  { complaint_id: 'NW-118820', date_opened: '2026-04-02', status: 'Closed', category: 'Service - missed appointment', region: 'Calderfield', priority: 'P3', days_open: 18, breached_live: false, routed_team: null, resolution_action: 'Appointment rebooked by agent' },
  { complaint_id: 'NW-119544', date_opened: '2026-05-11', status: 'Closed', category: 'Payment - plan or arrears', region: 'Eastmarch', priority: 'P3', days_open: 21, breached_live: true, routed_team: null, resolution_action: 'Payment plan amended' },
  { complaint_id: 'NW-121979', date_opened: '2026-07-06', status: 'Open', category: 'Service - poor communication', region: 'Calderfield', priority: 'P3', days_open: 86, breached_live: true, routed_team: 'Customer care leads', resolution_action: null },
]

export const accountHistory: AccountHistoryRow[] = [
  { account_id: 'ACC-120669', complaint_id: 'NW-104112', date_opened: '2025-02-11', category: 'Billing - disputed amount', status: 'Closed', complaint_seq: 1, complaints_on_account: 3, days_since_previous: null, is_repeat: false },
  { account_id: 'ACC-120669', complaint_id: 'NW-104190', date_opened: '2025-02-13', category: 'Billing - disputed amount', status: 'Closed - reopened', complaint_seq: 2, complaints_on_account: 3, days_since_previous: 2, is_repeat: true },
  { account_id: 'ACC-120669', complaint_id: 'NW-109833', date_opened: '2025-08-30', category: 'Billing - estimated read', status: 'Closed', complaint_seq: 3, complaints_on_account: 3, days_since_previous: 198, is_repeat: true },
  { account_id: 'ACC-337102', complaint_id: 'NW-111204', date_opened: '2025-10-04', category: 'Water - pressure or quality', status: 'Closed', complaint_seq: 1, complaints_on_account: 2, days_since_previous: null, is_repeat: false },
  { account_id: 'ACC-337102', complaint_id: 'NW-124487', date_opened: '2026-09-19', category: 'Water - pressure or quality', status: 'Open', complaint_seq: 2, complaints_on_account: 2, days_since_previous: 350, is_repeat: true },
  { account_id: 'ACC-455019', complaint_id: 'NW-107001', date_opened: '2025-06-02', category: 'Service - missed appointment', status: 'Closed', complaint_seq: 1, complaints_on_account: 2, days_since_previous: null, is_repeat: false },
  { account_id: 'ACC-455019', complaint_id: 'NW-122814', date_opened: '2026-08-17', category: 'Service - missed appointment', status: 'Open', complaint_seq: 2, complaints_on_account: 2, days_since_previous: 441, is_repeat: true },
]

export const agentResults: AgentResultRow[] = [
  { agent_id: 'billing', name: 'Billing', classified: 18, fast_lane: 0, runs: 0, drafts_pending: 0, drafts_approved: 0 },
  { agent_id: 'field_services', name: 'Field services', classified: 18, fast_lane: 0, runs: 0, drafts_pending: 0, drafts_approved: 0 },
  { agent_id: 'metering', name: 'Metering', classified: 6, fast_lane: 0, runs: 0, drafts_pending: 0, drafts_approved: 0 },
  { agent_id: 'customer_support', name: 'Customer support', classified: 6, fast_lane: 6, runs: 0, drafts_pending: 0, drafts_approved: 0 },
  { agent_id: 'general', name: 'General', classified: 6, fast_lane: 0, runs: 0, drafts_pending: 0, drafts_approved: 0 },
]

export const classificationSummary: ClassificationSummaryRow[] = [
  { group_name: 'Billing', classifications: 18, share_of_total: 0.3333, avg_group_confidence: 0.54, data_fallbacks: 6 },
  { group_name: 'Field services', classifications: 18, share_of_total: 0.3333, avg_group_confidence: 0.3, data_fallbacks: 18 },
  { group_name: 'Metering', classifications: 6, share_of_total: 0.1111, avg_group_confidence: 0.92, data_fallbacks: 0 },
  { group_name: 'Customer support', classifications: 6, share_of_total: 0.1111, avg_group_confidence: 0.4, data_fallbacks: 6 },
  { group_name: 'General', classifications: 6, share_of_total: 0.1111, avg_group_confidence: 0.38, data_fallbacks: 6 },
]

export const profiles: ProfileRow[] = [
  { category: 'Billing - disputed amount', region: 'Barrowdale', source_system: 'SYS-05', n: 319, avg_days: 33.2, info_only_share: 0.23, transfer_rate: 0.43, reopen_rate: 0.18, top_resolution: 'Bill corrected and re-issued' },
  { category: 'Billing - estimated read', region: 'Ashford', source_system: 'SYS-04', n: 161, avg_days: 25.1, info_only_share: 0.2, transfer_rate: 0, reopen_rate: 0.09, top_resolution: 'Bill corrected and re-issued' },
  { category: 'Metering - no read taken', region: 'Dunmoor', source_system: 'SYS-01', n: 142, avg_days: 28.6, info_only_share: 0.11, transfer_rate: 0.47, reopen_rate: 0.17, top_resolution: 'Meter visit required' },
  { category: 'Payment - plan or arrears', region: 'Eastmarch', source_system: 'SYS-03', n: 96, avg_days: 26.4, info_only_share: 0.26, transfer_rate: 0.46, reopen_rate: 0.16, top_resolution: 'Payment plan amended' },
  { category: 'Supply - interruption', region: 'Fenwick', source_system: 'SYS-05', n: 104, avg_days: 29.9, info_only_share: 0.25, transfer_rate: 0.46, reopen_rate: 0.17, top_resolution: 'Field repair required' },
  { category: 'Water - pressure or quality', region: 'Ashford', source_system: 'SYS-04', n: 71, avg_days: 23.5, info_only_share: 0.33, transfer_rate: 0, reopen_rate: 0.1, top_resolution: 'Field repair required' },
  { category: 'Service - missed appointment', region: 'Calderfield', source_system: 'SYS-03', n: 88, avg_days: 30.2, info_only_share: 0.12, transfer_rate: 0.45, reopen_rate: 0.17, top_resolution: 'Appointment rebooked by agent' },
  { category: 'Service - poor communication', region: 'Calderfield', source_system: 'SYS-01', n: 79, avg_days: 30.8, info_only_share: 0.53, transfer_rate: 0.47, reopen_rate: 0.16, top_resolution: 'Information provided only' },
]
