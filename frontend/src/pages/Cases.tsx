import { Link } from 'react-router-dom'
import { useCases } from '../api/reports'
import Badge, { PriorityBadge } from '../components/Badge'
import Card from '../components/Card'
import { DateField, FilterBar, SearchField, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import { CATEGORIES, CHANNELS, PRIORITIES, REGIONS, STATUSES } from '../constants'
import { useListParams } from '../hooks/useListParams'
import { serverTable } from '../lib/serverTable'
import type { CaseRow } from '../types'

const columns: Column<CaseRow>[] = [
  {
    key: 'complaint_id',
    header: 'Complaint',
    sortKey: 'complaint_id',
    cell: (r) => (
      <Link to={`/cases/${r.complaint_id}`} className="num text-brand hover:underline">
        {r.complaint_id}
      </Link>
    ),
  },
  { key: 'date_opened', header: 'Opened', sortKey: 'date_opened', cell: (r) => <span className="num text-gray-600">{r.date_opened}</span> },
  {
    key: 'status',
    header: 'Status',
    sortKey: 'status',
    cell: (r) => <Badge tone={r.status === 'Open' ? 'brand' : r.status === 'Closed' ? 'gray' : 'amber'}>{r.status}</Badge>,
  },
  {
    key: 'category',
    header: 'Category',
    sortKey: 'category',
    cell: (r) => (
      <div className="leading-snug">
        <div>{r.category}</div>
        <div className="text-xs text-gray-500">{r.region}</div>
      </div>
    ),
  },
  { key: 'classified_priority', header: 'Priority', sortKey: 'classified_priority', cell: (r) => <PriorityBadge priority={r.classified_priority} /> },
  { key: 'days_open', header: 'Age', align: 'right', sortKey: 'days_open', cell: (r) => <span className={r.breached_live ? 'num text-red-700' : 'num'}>{r.days_open}d</span> },
  {
    key: 'breached_live',
    header: 'SLA',
    cell: (r) => <Badge tone={r.breached_live ? 'red' : 'green'}>{r.breached_live ? 'Breached' : 'Within'}</Badge>,
  },
  {
    key: 'outcome',
    header: 'Team / outcome',
    sortKey: 'routed_team',
    cell: (r) => <span className="block max-w-48 whitespace-normal">{r.routed_team ?? r.resolution_action ?? '-'}</span>,
  },
]

export default function Cases() {
  const list = useListParams({ pageSize: 10 })
  const query = useCases(list.params)
  const f = list.filters

  return (
    <>
      <PageHeader title="Cases" description="Every complaint, open or closed. Filter to your team's queue and open a case to work it." />

      <FilterBar onClear={list.hasFilters ? list.clearFilters : undefined}>
        <SearchField placeholder="Complaint or account id" value={f.q} onChange={(v) => list.setFilter('q', v)} />
        <Select label="Status" options={STATUSES} value={f.status} onChange={(v) => list.setFilter('status', v)} />
        <Select label="Region" options={REGIONS} value={f.region} onChange={(v) => list.setFilter('region', v)} />
        <Select label="Category" options={CATEGORIES} value={f.category} onChange={(v) => list.setFilter('category', v)} />
        <Select label="Priority" options={PRIORITIES} value={f.classified_priority} onChange={(v) => list.setFilter('classified_priority', v)} />
        <Select label="Channel" options={CHANNELS} value={f.channel} onChange={(v) => list.setFilter('channel', v)} />
        <DateField label="Opened from" value={f.opened_from} onChange={(v) => list.setFilter('opened_from', v)} />
        <DateField label="Opened to" value={f.opened_to} onChange={(v) => list.setFilter('opened_to', v)} />
        <ToggleChip label="Breached" on={f.breached === 'true'} onChange={(on) => list.setToggle('breached', on)} />
        <ToggleChip label="Reopened" on={f.reopened === 'true'} onChange={(on) => list.setToggle('reopened', on)} />
        <ToggleChip label="Transferred" on={f.transferred === 'true'} onChange={(on) => list.setToggle('transferred', on)} />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={query.data?.items ?? []} rowKey={(r) => r.complaint_id} server={serverTable(list, query)} />
      </Card>
    </>
  )
}
