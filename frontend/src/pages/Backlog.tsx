import BarChart from '../components/BarChart'
import Card, { CardTitle } from '../components/Card'
import { FilterBar, Select, SegmentedControl } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, PRIORITIES, REGIONS, breakdown, flow } from '../mock'
import { num, pct } from '../lib/format'
import type { BreakdownRow } from '../types'

const columns: Column<BreakdownRow>[] = [
  { key: 'region', header: 'Region' },
  { key: 'open_cases', header: 'Open', align: 'right', cell: (r) => num(r.open_cases) },
  { key: 'breached_cases', header: 'Past target', align: 'right', cell: (r) => <span className="text-red-600">{num(r.breached_cases)}</span> },
  { key: 'at_risk_cases', header: 'At risk', align: 'right' },
  { key: 'total_days_overdue', header: 'Days overdue', align: 'right', cell: (r) => num(r.total_days_overdue) },
  {
    key: 'share_of_backlog',
    header: 'Share of backlog',
    align: 'right',
    cell: (r) => (
      <span className="inline-flex items-center justify-end gap-2">
        <span className="h-1.5 w-16 rounded-full bg-gray-100">
          <span className="block h-1.5 rounded-full bg-brand/75" style={{ width: `${r.share_of_backlog * 100 * 4}%` }} />
        </span>
        {pct(r.share_of_backlog, 1)}
      </span>
    ),
  },
]

export default function Backlog() {
  const last = flow[flow.length - 1]
  return (
    <>
      <PageHeader title="Backlog" description="How the backlog built up month by month, and where it sits today." />

      <StatRow>
        <StatCard label="Open backlog" value={num(last.backlog_end_of_month)} hint="End of Sep 2026" />
        <StatCard label="Opened in Sep" value={num(last.opened)} />
        <StatCard label="Closed in Sep" value={num(last.closed)} />
        <StatCard label="Net change in Sep" value={`+${last.net_change}`} hint="Opened minus closed" />
      </StatRow>

      <FilterBar>
        <Select label="Region" options={REGIONS} />
        <Select label="Category" options={CATEGORIES} />
        <Select label="Priority" options={PRIORITIES} />
        <Select label="From month" options={flow.map((f) => f.month)} />
        <Select label="To month" options={flow.map((f) => f.month)} />
      </FilterBar>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle title="Open backlog at the end of each month" hint="Oct 2024 to Sep 2026" />
          <BarChart data={flow.map((f) => ({ label: f.month, value: f.backlog_end_of_month }))} height={300} />
        </Card>
        <Card>
          <CardTitle title="Opened and closed each month" hint="The backlog grows whenever more come in than go out" />
          <p className="mb-2 text-xs font-medium text-gray-500">Opened</p>
          <BarChart data={flow.map((f) => ({ label: f.month, value: f.opened }))} height={120} />
          <p className="mt-5 mb-2 text-xs font-medium text-gray-500">Closed</p>
          <BarChart data={flow.map((f) => ({ label: f.month, value: f.closed }))} height={120} />
        </Card>
      </div>

      <Card>
        <CardTitle
          title="Open backlog by group"
          hint="Choose how to group the 1,599 open complaints"
          action={<SegmentedControl label="" options={['Region', 'Category', 'Domain', 'Priority', 'Age']} />}
        />
        <DataTable columns={columns} rows={breakdown} rowKey={(r) => r.region} pageSize={10} />
      </Card>
    </>
  )
}
