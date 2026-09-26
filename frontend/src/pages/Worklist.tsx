import { Link } from 'react-router-dom'
import { LaneBadge, PriorityBadge } from '../components/Badge'
import Card from '../components/Card'
import { FilterBar, Select, SearchField, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, LANES, PRIORITIES, REGIONS, TEAMS, worklist } from '../mock'
import type { WorklistRow } from '../types'

const columns: Column<WorklistRow>[] = [
  {
    key: 'complaint_id',
    header: 'Complaint',
    cell: (r) => (
      <div className="leading-tight">
        <Link to={`/cases/${r.complaint_id}`} className="font-medium text-purple-600 hover:underline">
          {r.complaint_id}
        </Link>
        <div className="text-xs text-gray-400">{r.account_id}</div>
      </div>
    ),
  },
  { key: 'category', header: 'Category' },
  { key: 'region', header: 'Region' },
  {
    key: 'classified_priority',
    header: 'Priority',
    cell: (r) => (
      <span className="inline-flex items-center gap-1.5">
        <PriorityBadge priority={r.classified_priority} />
        {r.classified_priority !== r.priority && <span className="text-xs text-gray-400">was {r.priority}</span>}
      </span>
    ),
  },
  {
    key: 'days_overdue',
    header: 'Days overdue',
    align: 'right',
    cell: (r) =>
      r.days_overdue > 0 ? (
        <span className="font-medium text-red-600">{r.days_overdue}</span>
      ) : (
        <span className="text-gray-400">{Math.abs(r.days_overdue)} left</span>
      ),
  },
  { key: 'routed_team', header: 'Team', cell: (r) => r.routed_team ?? <span className="text-gray-300">Not classified</span> },
  { key: 'lane', header: 'Lane', cell: (r) => <LaneBadge lane={r.lane} /> },
  {
    key: 'next_action',
    header: 'Next action',
    cell: (r) => (r.next_action ? <span className="block max-w-56 whitespace-normal">{r.next_action}</span> : <span className="text-gray-300">-</span>),
  },
]

export default function Worklist() {
  return (
    <>
      <PageHeader
        title="Worklist"
        description="Open complaints, most urgent first: priority after the classifier's flags, then days past the SLA target."
      />

      <StatRow>
        <StatCard label="Open complaints" value="1,599" hint="As of 30 Sep 2026" />
        <StatCard label="Past SLA target" value="841" hint="53% of the backlog" />
        <StatCard label="At risk" value="143" hint="Over 75% of the target used" />
        <StatCard label="Classified" value="54" hint="The rest are waiting for the classifier" />
      </StatRow>

      <FilterBar>
        <SearchField placeholder="Complaint or account id" />
        <Select label="Region" options={REGIONS} />
        <Select label="Category" options={CATEGORIES} />
        <Select label="Priority" options={PRIORITIES} />
        <Select label="Team" options={TEAMS} />
        <Select label="Lane" options={LANES.map((l) => l.replace('_', ' '))} />
        <ToggleChip label="Past target" />
        <ToggleChip label="Not classified" />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={worklist} rowKey={(r) => r.complaint_id} pageSize={10} total={1599} />
      </Card>
    </>
  )
}
