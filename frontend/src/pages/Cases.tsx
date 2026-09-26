import { Link } from 'react-router-dom'
import Badge, { PriorityBadge } from '../components/Badge'
import Card from '../components/Card'
import { DateField, FilterBar, SearchField, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import { CATEGORIES, CHANNELS, PRIORITIES, REGIONS, cases } from '../mock'
import type { CaseRow } from '../types'

const columns: Column<CaseRow>[] = [
  {
    key: 'complaint_id',
    header: 'Complaint',
    cell: (r) => (
      <Link to={`/cases/${r.complaint_id}`} className="font-medium text-purple-600 hover:underline">
        {r.complaint_id}
      </Link>
    ),
  },
  { key: 'date_opened', header: 'Opened' },
  {
    key: 'status',
    header: 'Status',
    cell: (r) => <Badge tone={r.status === 'Open' ? 'purple' : r.status === 'Closed' ? 'gray' : 'amber'}>{r.status}</Badge>,
  },
  { key: 'category', header: 'Category' },
  { key: 'region', header: 'Region' },
  { key: 'priority', header: 'Priority', cell: (r) => <PriorityBadge priority={r.priority} /> },
  { key: 'days_open', header: 'Days', align: 'right' },
  {
    key: 'breached_live',
    header: 'SLA',
    cell: (r) => <Badge tone={r.breached_live ? 'red' : 'green'}>{r.breached_live ? 'Breached' : 'Within'}</Badge>,
  },
  {
    key: 'outcome',
    header: 'Team or outcome',
    sortValue: (r) => r.routed_team ?? r.resolution_action,
    cell: (r) => <span className="block max-w-48 whitespace-normal">{r.routed_team ?? r.resolution_action ?? '-'}</span>,
  },
]

export default function Cases() {
  return (
    <>
      <PageHeader title="Cases" description="Search every complaint, open or closed, and open one to see its full context." />

      <FilterBar>
        <SearchField placeholder="Complaint or account id" />
        <Select label="Status" options={['Open', 'Closed', 'Closed - reopened']} />
        <Select label="Region" options={REGIONS} />
        <Select label="Category" options={CATEGORIES} />
        <Select label="Priority" options={PRIORITIES} />
        <Select label="Channel" options={CHANNELS} />
        <DateField label="Opened from" />
        <DateField label="Opened to" />
        <ToggleChip label="Breached" />
        <ToggleChip label="Reopened" />
        <ToggleChip label="Transferred" />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={cases} rowKey={(r) => r.complaint_id} pageSize={10} total={25416} />
      </Card>
    </>
  )
}
