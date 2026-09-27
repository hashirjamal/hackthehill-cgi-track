import { useMemo } from 'react'
import { useBacklogBreakdown, useBacklogFlow } from '../api/reports'
import { PriorityBadge } from '../components/Badge'
import Badge from '../components/Badge'
import BarChart from '../components/BarChart'
import Card, { CardTitle } from '../components/Card'
import { FilterBar, SegmentedControl, Select } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import QueryState from '../components/QueryState'
import Skeleton from '../components/Skeleton'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, MONTHS, PRIORITIES, REGIONS } from '../constants'
import { useListParams } from '../hooks/useListParams'
import { num, pct } from '../lib/format'
import { serverTable } from '../lib/serverTable'
import type { BreakdownRow, Priority } from '../types'

const GROUPS = [
  { value: 'region', label: 'Region' },
  { value: 'category', label: 'Category' },
  { value: 'domain', label: 'AI agent' },
  { value: 'priority', label: 'Priority' },
  { value: 'age_band', label: 'Age' },
  { value: 'breached_live', label: 'SLA status' },
  { value: 'channel', label: 'Channel' },
  { value: 'source_system', label: 'Source system' },
]

/** How a group's value is drawn: a badge for priority and SLA status, plain text otherwise. */
function groupCell(group: string, row: BreakdownRow) {
  const value = row[group]
  if (group === 'priority') return <PriorityBadge priority={value as Priority} />
  if (group === 'breached_live') return <Badge tone={value ? 'red' : 'green'}>{value ? 'Past target' : 'Within target'}</Badge>
  if (group === 'age_band') return `${value} days`
  return String(value ?? '')
}

const ChartSkeleton = ({ height }: { height: number }) => <Skeleton className="w-full" style={{ height }} />

export default function Backlog() {
  const list = useListParams({ pageSize: 10 })
  const f = list.filters
  const group = GROUPS.some((g) => g.value === f.group_by) ? f.group_by : 'region'

  // Region, category and priority narrow everything on the page. The months only limit the history charts.
  const narrow = { region: f.region, category: f.category, priority: f.priority }
  const flow = useBacklogFlow({ ...narrow, month_from: f.month_from, month_to: f.month_to, page_size: 200 })
  const breakdown = useBacklogBreakdown({ ...narrow, group_by: group, page: list.page, page_size: list.pageSize, sort: list.sort })

  const months = flow.data?.items ?? []
  const latest = months[months.length - 1]

  // The table is drawn for the grouping of the rows on screen. While a new grouping loads, the previous rows
  // stay visible, so the columns must not switch to the new grouping before its rows arrive.
  const shownGroup = breakdown.data?.group_by?.[0] ?? group

  const columns = useMemo<Column<BreakdownRow>[]>(
    () => [
      { key: shownGroup, header: GROUPS.find((g) => g.value === shownGroup)?.label ?? shownGroup, sortKey: shownGroup, cell: (r) => groupCell(shownGroup, r) },
      { key: 'open_cases', header: 'Open', align: 'right', sortKey: 'open_cases', cell: (r) => num(r.open_cases) },
      { key: 'breached_cases', header: 'Past target', align: 'right', sortKey: 'breached_cases', cell: (r) => <span className="text-red-600">{num(r.breached_cases)}</span> },
      { key: 'at_risk_cases', header: 'At risk', align: 'right', sortKey: 'at_risk_cases' },
      { key: 'total_days_overdue', header: 'Days overdue', align: 'right', sortKey: 'total_days_overdue', cell: (r) => num(r.total_days_overdue) },
      { key: 'avg_days_open', header: 'Avg days open', align: 'right', sortKey: 'avg_days_open' },
      {
        key: 'share_of_backlog',
        header: 'Share of backlog',
        align: 'right',
        sortKey: 'share_of_backlog',
        cell: (r) => (
          <span className="inline-flex items-center justify-end gap-2">
            <span className="h-1.5 w-16 rounded-full bg-gray-100">
              <span className="block h-1.5 rounded-full bg-brand/75" style={{ width: `${Math.min(r.share_of_backlog * 100 * 3, 100)}%` }} />
            </span>
            {pct(r.share_of_backlog, 1)}
          </span>
        ),
      },
    ],
    [shownGroup],
  )

  const monthLabel = latest ? latest.month : ''
  return (
    <>
      <PageHeader title="Backlog" description="How the backlog built up month by month, and where it sits today." />

      <StatRow>
        <StatCard label="Open backlog" value={num(latest?.backlog_end_of_month ?? 0)} hint={`End of ${monthLabel}`} loading={flow.isPending} error={flow.isError && !latest} />
        <StatCard label={`Opened in ${monthLabel || 'the latest month'}`} value={num(latest?.opened ?? 0)} loading={flow.isPending} error={flow.isError && !latest} />
        <StatCard label={`Closed in ${monthLabel || 'the latest month'}`} value={num(latest?.closed ?? 0)} loading={flow.isPending} error={flow.isError && !latest} />
        <StatCard
          label="Net change"
          value={latest ? `${latest.net_change > 0 ? '+' : ''}${num(latest.net_change)}` : ''}
          hint="Opened minus closed"
          loading={flow.isPending}
          error={flow.isError && !latest}
        />
      </StatRow>

      <FilterBar onClear={Object.keys(f).some((k) => k !== 'group_by') ? () => list.clearFilters() : undefined}>
        <Select label="Region" options={REGIONS} value={f.region} onChange={(v) => list.setFilter('region', v)} />
        <Select label="Category" options={CATEGORIES} value={f.category} onChange={(v) => list.setFilter('category', v)} />
        <Select label="Priority" options={PRIORITIES} value={f.priority} onChange={(v) => list.setFilter('priority', v)} />
        <Select label="From month" options={MONTHS} value={f.month_from} onChange={(v) => list.setFilter('month_from', v)} />
        <Select label="To month" options={MONTHS} value={f.month_to} onChange={(v) => list.setFilter('month_to', v)} />
      </FilterBar>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle title="Open backlog at the end of each month" hint="Grows whenever more come in than go out" />
          <QueryState query={flow} skeleton={<ChartSkeleton height={300} />}>
            {(data) => <BarChart data={data.items.map((m) => ({ label: m.month, value: m.backlog_end_of_month }))} height={300} />}
          </QueryState>
        </Card>
        <Card>
          <CardTitle title="Opened and closed each month" />
          <QueryState query={flow} skeleton={<ChartSkeleton height={300} />}>
            {(data) => (
              <>
                <p className="mb-2 text-xs font-medium text-gray-500">Opened</p>
                <BarChart data={data.items.map((m) => ({ label: m.month, value: m.opened }))} height={120} />
                <p className="mt-5 mb-2 text-xs font-medium text-gray-500">Closed</p>
                <BarChart data={data.items.map((m) => ({ label: m.month, value: m.closed }))} height={120} />
              </>
            )}
          </QueryState>
        </Card>
      </div>

      <Card>
        <CardTitle
          title="Open backlog by group"
          hint="Choose how to group today's open complaints"
          action={
            <SegmentedControl
              label=""
              options={GROUPS}
              value={group}
              onChange={(v) => {
                // A new grouping has its own columns, so the old sort and page no longer apply.
                list.setMany({ group_by: v === 'region' ? undefined : v, sort: undefined })
              }}
            />
          }
        />
        <DataTable
          columns={columns}
          rows={breakdown.data?.items ?? []}
          rowKey={(r) => String(r[shownGroup])}
          // Sorting and paging follow the breakdown's own query, and the URL's sort is cleared when the grouping changes.
          server={serverTable(list, breakdown)}
        />
      </Card>
    </>
  )
}
