// Values the filters offer. They match the data, and the API accepts any of them.
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
export const LANES = [
  { value: 'emergency', label: 'Emergency' },
  { value: 'review', label: 'Review' },
  { value: 'quick_lane', label: 'Quick lane' },
  { value: 'standard', label: 'Standard' },
]
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
export const STATUSES = ['Open', 'Closed', 'Closed - reopened']
export const SOURCE_SYSTEMS = ['SYS-01', 'SYS-03', 'SYS-04', 'SYS-05']
