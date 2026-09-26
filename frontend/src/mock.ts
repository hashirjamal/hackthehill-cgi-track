// Sample data for the first build. Shapes match the reporting API, so each page can switch to a fetch later.
import type {
  AccountHistoryRow,
  AgentResultRow,
  BreakdownRow,
  CaseRow,
  ClassificationSummaryRow,
  ClusterRow,
  FlowRow,
  ProfileRow,
  RootCauseRow,
  WorklistRow,
} from './types'

export const REGIONS = ['Ashford', 'Barrowdale', 'Calderfield', 'Dunmoor', 'Eastmarch', 'Fenwick']
export const CATEGORIES = [
  'Billing - disputed amount',
  'Billing - estimated read',
  'Metering - no read taken',
  'Payment - plan or arrears',
  'Supply - interruption',
  'Water - pressure or quality',
  'Service - missed appointment',
  'Service - poor communication',
  'Other',
]
export const PRIORITIES = ['P1', 'P2', 'P3']
export const LANES = ['emergency', 'review', 'quick_lane', 'standard']
export const CHANNELS = ['Phone', 'Web form', 'Email', 'Social', 'Post', 'Regulator referral']
export const TEAMS = [
  'Billing team',
  'Metering team',
  'Collections',
  'Network operations',
  'Water operations',
  'Field services',
  'Customer care leads',
  'General review queue',
]

export const worklist: WorklistRow[] = [
  { complaint_id: 'NW-124358', account_id: 'ACC-610284', category: 'Supply - interruption', region: 'Fenwick', priority: 'P1', classified_priority: 'P1', days_overdue: 13, breached_live: true, domain: 'field_services', routed_team: 'Network operations', lane: 'standard', likely_cause: null, next_action: 'Dispatch an engineer' },
  { complaint_id: 'NW-124487', account_id: 'ACC-337102', category: 'Water - pressure or quality', region: 'Ashford', priority: 'P1', classified_priority: 'P1', days_overdue: 11, breached_live: true, domain: 'field_services', routed_team: 'Water operations', lane: 'standard', likely_cause: null, next_action: 'Book a field repair' },
  { complaint_id: 'NW-120404', account_id: 'ACC-943644', category: 'Billing - estimated read', region: 'Barrowdale', priority: 'P3', classified_priority: 'P2', days_overdue: 106, breached_live: true, domain: 'billing', routed_team: 'Metering team', lane: 'standard', likely_cause: 'estimated_reading', next_action: 'Take a real reading, then correct the bill' },
  { complaint_id: 'NW-120856', account_id: 'ACC-592536', category: 'Billing - disputed amount', region: 'Dunmoor', priority: 'P3', classified_priority: 'P2', days_overdue: 94, breached_live: true, domain: 'billing', routed_team: 'Billing team', lane: 'standard', likely_cause: 'estimated_reading', next_action: 'Review the disputed charge' },
  { complaint_id: 'NW-122297', account_id: 'ACC-830825', category: 'Payment - plan or arrears', region: 'Eastmarch', priority: 'P2', classified_priority: 'P2', days_overdue: 57, breached_live: true, domain: 'billing', routed_team: 'Collections', lane: 'standard', likely_cause: null, next_action: 'Offer a payment plan' },
  { complaint_id: 'NW-122814', account_id: 'ACC-455019', category: 'Service - missed appointment', region: 'Calderfield', priority: 'P3', classified_priority: 'P2', days_overdue: 44, breached_live: true, domain: 'field_services', routed_team: 'Field services', lane: 'standard', likely_cause: null, next_action: 'Rebook the appointment' },
  { complaint_id: 'NW-121979', account_id: 'ACC-563523', category: 'Service - poor communication', region: 'Calderfield', priority: 'P3', classified_priority: 'P3', days_overdue: 2, breached_live: true, domain: 'customer_support', routed_team: 'Customer care leads', lane: 'quick_lane', likely_cause: null, next_action: 'Approve the drafted reply' },
  { complaint_id: 'NW-124911', account_id: 'ACC-208871', category: 'Metering - no read taken', region: 'Dunmoor', priority: 'P3', classified_priority: 'P3', days_overdue: -8, breached_live: false, domain: 'metering', routed_team: 'Metering team', lane: null, likely_cause: null, next_action: null },
  { complaint_id: 'NW-124760', account_id: 'ACC-771640', category: 'Other', region: 'Fenwick', priority: 'P3', classified_priority: 'P3', days_overdue: -12, breached_live: false, domain: 'general', routed_team: 'General review queue', lane: 'review', likely_cause: null, next_action: 'Review and route' },
  { complaint_id: 'NW-124802', account_id: 'ACC-119033', category: 'Billing - disputed amount', region: 'Ashford', priority: 'P2', classified_priority: 'P2', days_overdue: -3, breached_live: false, domain: 'billing', routed_team: 'Billing team', lane: null, likely_cause: null, next_action: null },
]

// Opened and closed per month, Oct 2024 to Sep 2026. The backlog is worked out from them.
const OPENED = [912, 830, 951, 985, 851, 901, 1023, 1004, 982, 1222, 1026, 1020, 1189, 940, 1120, 1177, 1002, 1171, 1190, 1049, 1164, 1271, 1185, 1251]
const CLOSED = [476, 760, 873, 927, 840, 901, 952, 942, 965, 1062, 1089, 1000, 1029, 1067, 1019, 1025, 1000, 1117, 1109, 1146, 1063, 1163, 1130, 1162]

export const flow: FlowRow[] = (() => {
  let backlog = 0
  return OPENED.map((opened, i) => {
    const closed = CLOSED[i]
    backlog += opened - closed
    const d = new Date(2024, 9 + i, 1)
    return {
      month: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`,
      opened,
      closed,
      net_change: opened - closed,
      backlog_end_of_month: backlog,
    }
  })
})()

export const breakdown: BreakdownRow[] = [
  { region: 'Fenwick', open_cases: 284, breached_cases: 155, at_risk_cases: 21, total_days_overdue: 2652, share_of_backlog: 0.1776 },
  { region: 'Barrowdale', open_cases: 275, breached_cases: 143, at_risk_cases: 28, total_days_overdue: 2535, share_of_backlog: 0.172 },
  { region: 'Calderfield', open_cases: 270, breached_cases: 148, at_risk_cases: 26, total_days_overdue: 2428, share_of_backlog: 0.1689 },
  { region: 'Eastmarch', open_cases: 268, breached_cases: 140, at_risk_cases: 24, total_days_overdue: 2339, share_of_backlog: 0.1676 },
  { region: 'Dunmoor', open_cases: 259, breached_cases: 134, at_risk_cases: 22, total_days_overdue: 2283, share_of_backlog: 0.162 },
  { region: 'Ashford', open_cases: 243, breached_cases: 121, at_risk_cases: 22, total_days_overdue: 3161, share_of_backlog: 0.152 },
]

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
