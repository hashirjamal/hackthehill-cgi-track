import { Loader2, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useClassify, useWorklist, useWorklistTotal, type ClassifyComplaint } from '../api/reports'
import Badge, { LaneBadge, PriorityBadge } from '../components/Badge'
import Card from '../components/Card'
import { Button, FilterBar, SearchField, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, LANES, PRIORITIES, REGIONS, TEAMS } from '../constants'
import { useListParams } from '../hooks/useListParams'
import { num, pct } from '../lib/format'
import type { WorklistRow } from '../types'

const CLASSIFY_AT_A_TIME = 10
const SUMMARY = 'the summary numbers' // one toast if they all fail

const columns: Column<WorklistRow>[] = [
  {
    key: 'complaint_id',
    header: 'Complaint',
    sortKey: 'complaint_id',
    cell: (r) => (
      <div className="leading-tight">
        <Link to={`/cases/${r.complaint_id}`} className="font-medium text-brand hover:underline">
          {r.complaint_id}
        </Link>
        <div className="text-xs text-gray-500">{r.account_id}</div>
      </div>
    ),
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
  {
    key: 'classified_priority',
    header: 'Priority',
    sortKey: 'classified_priority',
    cell: (r) => (
      <div className="leading-tight">
        <PriorityBadge priority={r.classified_priority} />
        {r.classified_priority !== r.priority && <div className="mt-1 text-xs text-gray-500">was {r.priority}</div>}
      </div>
    ),
  },
  {
    key: 'days_overdue',
    header: 'Days overdue',
    align: 'right',
    sortKey: 'days_overdue',
    cell: (r) =>
      r.days_overdue > 0 ? (
        <span className="font-medium text-red-600">{r.days_overdue}</span>
      ) : (
        <span className="text-gray-500">{Math.abs(r.days_overdue)} left</span>
      ),
  },
  {
    key: 'routed_team',
    header: 'Team',
    sortKey: 'routed_team',
    cell: (r) => r.routed_team ?? <span className="text-gray-400">Not classified</span>,
  },
  { key: 'lane', header: 'Lane', sortKey: 'lane', cell: (r) => <LaneBadge lane={r.lane} /> },
  {
    key: 'likely_cause',
    header: 'Likely cause',
    cell: (r) => (r.likely_cause === 'estimated_reading' ? <Badge tone="brand">Estimated reading</Badge> : <span className="text-gray-300">-</span>),
  },
]

export default function Worklist() {
  const list = useListParams({ pageSize: 10 })
  const query = useWorklist(list.params)
  const classify = useClassify()

  // The stat cards ask for one row each, just to read the total.
  const open = useWorklistTotal({}, SUMMARY)
  const breached = useWorklistTotal({ breached: true }, SUMMARY)
  const overdue = useWorklistTotal({ days_overdue_min: 30 }, SUMMARY)
  const classified = useWorklistTotal({ classified: true }, SUMMARY)

  const rows = query.data?.items ?? []
  const toClassify = rows.filter((r) => r.classification_id === null).slice(0, CLASSIFY_AT_A_TIME)

  const runClassify = () =>
    classify.mutate(
      toClassify.map<ClassifyComplaint>((r) => ({
        complaint_id: r.complaint_id,
        category: r.category,
        priority: r.priority,
        sla_days: r.sla_days,
        channel: r.channel,
        region: r.region,
        source_system: r.source_system,
        date_opened: r.date_opened,
        account_id: r.account_id,
      })),
    )

  const f = list.filters
  return (
    <>
      <PageHeader
        title="Worklist"
        description="Open complaints, most urgent first: priority after the classifier's flags, then days past the SLA target."
        actions={
          <Button onClick={runClassify} disabled={toClassify.length === 0 || classify.isPending || query.isPending}>
            <span className="inline-flex items-center gap-2">
              {classify.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {classify.isPending
                ? 'Classifying…'
                : query.isPending
                  ? 'Classify this page'
                  : toClassify.length === 0
                    ? 'Nothing to classify here'
                    : `Classify ${toClassify.length} on this page`}
            </span>
          </Button>
        }
      />

      <StatRow>
        <StatCard label="Open complaints" value={num(open.data ?? 0)} hint="As of 30 Sep 2026" loading={open.isPending} error={open.isError} />
        <StatCard
          label="Past SLA target"
          value={num(breached.data ?? 0)}
          hint={open.data ? `${pct((breached.data ?? 0) / open.data)} of the backlog` : undefined}
          loading={breached.isPending}
          error={breached.isError}
        />
        <StatCard label="Over 30 days late" value={num(overdue.data ?? 0)} hint="Days past the target" loading={overdue.isPending} error={overdue.isError} />
        <StatCard
          label="Classified"
          value={num(classified.data ?? 0)}
          hint="The rest are waiting for the classifier"
          loading={classified.isPending}
          error={classified.isError}
        />
      </StatRow>

      <FilterBar onClear={list.hasFilters ? list.clearFilters : undefined}>
        <SearchField placeholder="Complaint or account id" value={f.q} onChange={(v) => list.setFilter('q', v)} />
        <Select label="Region" options={REGIONS} value={f.region} onChange={(v) => list.setFilter('region', v)} />
        <Select label="Category" options={CATEGORIES} value={f.category} onChange={(v) => list.setFilter('category', v)} />
        <Select label="Priority" options={PRIORITIES} value={f.classified_priority} onChange={(v) => list.setFilter('classified_priority', v)} />
        <Select label="Team" options={TEAMS} value={f.routed_team} onChange={(v) => list.setFilter('routed_team', v)} />
        <Select label="Lane" options={LANES} value={f.lane} onChange={(v) => list.setFilter('lane', v)} />
        <ToggleChip label="Past target" on={f.breached === 'true'} onChange={(on) => list.setToggle('breached', on)} />
        <ToggleChip label="Not classified" on={f.classified === 'false'} onChange={(on) => list.setFilter('classified', on ? 'false' : undefined)} />
      </FilterBar>

      <Card>
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.complaint_id}
          server={{
            // The numbers of the rows on screen, which are the previous page's while the next one loads.
            page: query.data?.page ?? list.page,
            pageSize: query.data?.page_size ?? list.pageSize,
            total: query.data?.total ?? 0,
            totalPages: query.data?.total_pages ?? 1,
            sort: list.sort,
            onPageChange: list.setPage,
            onPageSizeChange: list.setPageSize,
            onSortChange: list.setSort,
            isLoading: query.isPending,
            isFetching: query.isFetching,
            error: query.error,
            onRetry: () => void query.refetch(),
            onClearFilters: list.hasFilters ? list.clearFilters : undefined,
          }}
        />
      </Card>
    </>
  )
}
