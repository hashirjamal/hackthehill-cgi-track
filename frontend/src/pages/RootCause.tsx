import { useMemo } from 'react'
import { useRootCause, useRootCauseClusters } from '../api/reports'
import Badge from '../components/Badge'
import Card, { CardTitle } from '../components/Card'
import { FilterBar, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, MONTHS, REGIONS } from '../constants'
import { useListParams } from '../hooks/useListParams'
import { num, pct } from '../lib/format'
import { serverTable } from '../lib/serverTable'
import { correlation } from '../lib/stats'
import type { ClusterRow, RootCauseRow } from '../types'

const HIGH_ESTIMATE = 0.4 // the API's own cut-off for an estimation-prone region

const rateBar = (rate: number) => (
  <span className="inline-flex items-center justify-end gap-2">
    <span className="h-1.5 w-20 rounded-full bg-gray-100">
      <span className="block h-1.5 rounded-full bg-brand/75" style={{ width: `${rate * 100}%` }} />
    </span>
    {pct(rate)}
  </span>
)

const monthColumns: Column<RootCauseRow>[] = [
  { key: 'month', header: 'Month', sortKey: 'month' },
  { key: 'region', header: 'Region', sortKey: 'region' },
  { key: 'estimated_read_rate', header: 'Estimated reads', align: 'right', sortKey: 'estimated_read_rate', cell: (r) => rateBar(r.estimated_read_rate) },
  { key: 'smart_meter_penetration', header: 'Smart meters', align: 'right', sortKey: 'smart_meter_penetration', cell: (r) => pct(r.smart_meter_penetration) },
  { key: 'billing_exceptions_per_1000', header: 'Billing exceptions / 1,000', align: 'right', sortKey: 'billing_exceptions_per_1000' },
  { key: 'complaints', header: 'Complaints', align: 'right', sortKey: 'complaints' },
  { key: 'billing_metering_per_1000', header: 'Billing and metering / 1,000', align: 'right', sortKey: 'billing_metering_per_1000' },
]

const clusterColumns: Column<ClusterRow>[] = [
  { key: 'region', header: 'Region', sortKey: 'region' },
  { key: 'category', header: 'Category', sortKey: 'category' },
  { key: 'open_cases', header: 'Open', align: 'right', sortKey: 'open_cases' },
  { key: 'breached_cases', header: 'Past target', align: 'right', sortKey: 'breached_cases', cell: (r) => <span className="text-red-600">{r.breached_cases}</span> },
  { key: 'share_of_region_backlog', header: 'Share of region', align: 'right', sortKey: 'share_of_region_backlog', cell: (r) => pct(r.share_of_region_backlog, 1) },
  {
    key: 'region_estimated_read_rate',
    header: 'Region estimated reads',
    align: 'right',
    sortKey: 'region_estimated_read_rate',
    cell: (r) => (r.region_estimated_read_rate === null ? '-' : pct(r.region_estimated_read_rate)),
  },
  {
    key: 'estimation_driven',
    header: 'Likely cause',
    sortKey: 'estimation_driven',
    cell: (r) => (r.estimation_driven ? <Badge tone="brand">Estimated readings</Badge> : <span className="text-gray-300">-</span>),
  },
]

export default function RootCause() {
  // Two tables, each with its own paging, sorting and filters in the URL. The second one's keys start with "c_".
  const months = useListParams({ pageSize: 10, others: ['c_'] })
  const clusters = useListParams({ pageSize: 10, prefix: 'c_' })
  const mf = months.filters
  const cf = clusters.filters

  const monthsQuery = useRootCause(months.params)
  const clustersQuery = useRootCauseClusters(clusters.params)

  // The stat cards look at everything, whatever the tables are filtered to.
  const all = useRootCause({ page_size: 200 }, 'the summary numbers')
  const drivenOpen = useRootCauseClusters({ estimation_driven: true, page_size: 200 }, 'the summary numbers')

  const stats = useMemo(() => {
    const rows = all.data?.items ?? []
    if (rows.length === 0) return null
    const latest = rows.reduce((m, r) => (r.month > m ? r.month : m), '')
    const now = rows.filter((r) => r.month === latest)
    const top = now.reduce((a, b) => (b.estimated_read_rate > a.estimated_read_rate ? b : a))
    const low = now.reduce((a, b) => (b.estimated_read_rate < a.estimated_read_rate ? b : a))
    return {
      latest,
      top,
      low,
      highRegions: now.filter((r) => r.estimated_read_rate >= HIGH_ESTIMATE).map((r) => r.region),
      r: correlation(rows.map((x) => x.estimated_read_rate), rows.map((x) => x.billing_metering_per_1000)),
    }
  }, [all.data])

  const drivenTotal = (drivenOpen.data?.items ?? []).reduce((s, c) => s + c.open_cases, 0)

  return (
    <>
      <PageHeader
        title="Root cause"
        description="Where complaints start: regions with more estimated readings raise more billing and metering complaints."
      />

      <StatRow>
        <StatCard
          label="Highest estimated reads"
          value={stats ? pct(stats.top.estimated_read_rate) : ''}
          hint={stats ? `${stats.top.region}, ${stats.latest}` : undefined}
          loading={all.isPending}
          error={all.isError}
        />
        <StatCard
          label="Lowest estimated reads"
          value={stats ? pct(stats.low.estimated_read_rate) : ''}
          hint={stats ? `${stats.low.region}, ${stats.latest}` : undefined}
          loading={all.isPending}
          error={all.isError}
        />
        <StatCard
          label="Correlation"
          value={stats?.r == null ? '-' : stats.r.toFixed(2)}
          hint="Estimated reads against billing and metering complaints"
          loading={all.isPending}
          error={all.isError}
        />
        <StatCard
          label="Open, estimation driven"
          value={num(drivenTotal)}
          hint={stats ? stats.highRegions.join(' and ') || 'No region over 40%' : undefined}
          loading={drivenOpen.isPending}
          error={drivenOpen.isError}
        />
      </StatRow>

      <FilterBar onClear={months.hasFilters ? months.clearFilters : undefined}>
        <Select label="Region" options={REGIONS} value={mf.region} onChange={(v) => months.setFilter('region', v)} />
        <Select label="From month" options={MONTHS} value={mf.month_from} onChange={(v) => months.setFilter('month_from', v)} />
        <Select label="To month" options={MONTHS} value={mf.month_to} onChange={(v) => months.setFilter('month_to', v)} />
        <ToggleChip
          label="High estimates only (40%+)"
          on={mf.estimated_read_rate_min === String(HIGH_ESTIMATE)}
          onChange={(on) => months.setFilter('estimated_read_rate_min', on ? String(HIGH_ESTIMATE) : undefined)}
        />
      </FilterBar>

      <Card>
        <CardTitle title="Region and month" hint="Estimated-read rate next to billing and metering complaints" />
        <DataTable columns={monthColumns} rows={monthsQuery.data?.items ?? []} rowKey={(r) => `${r.month}-${r.region}`} server={serverTable(months, monthsQuery)} />
      </Card>

      <Card>
        <CardTitle title="Open complaints by region and category" hint="Clusters in today's backlog, next to the region's meter data" />
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Select label="Region" options={REGIONS} value={cf.region} onChange={(v) => clusters.setFilter('region', v)} />
          <Select label="Category" options={CATEGORIES} value={cf.category} onChange={(v) => clusters.setFilter('category', v)} />
          <ToggleChip label="Estimation driven only" on={cf.estimation_driven === 'true'} onChange={(on) => clusters.setToggle('estimation_driven', on)} />
          {clusters.hasFilters && (
            <button type="button" onClick={clusters.clearFilters} className="rounded-xl px-3 py-2 text-sm font-medium text-brand hover:bg-brand-soft">
              Clear filters
            </button>
          )}
        </div>
        <DataTable columns={clusterColumns} rows={clustersQuery.data?.items ?? []} rowKey={(r) => `${r.region}-${r.category}`} server={serverTable(clusters, clustersQuery)} />
      </Card>
    </>
  )
}
