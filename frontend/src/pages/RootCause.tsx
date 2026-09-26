import Badge from '../components/Badge'
import Card, { CardTitle } from '../components/Card'
import { FilterBar, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, REGIONS, clusters, rootCause } from '../mock'
import { pct } from '../lib/format'
import type { ClusterRow, RootCauseRow } from '../types'

const rateBar = (rate: number) => (
  <span className="inline-flex items-center justify-end gap-2">
    <span className="h-1.5 w-20 rounded-full bg-gray-100">
      <span className="block h-1.5 rounded-full bg-purple-500/80" style={{ width: `${rate * 100}%` }} />
    </span>
    {pct(rate)}
  </span>
)

const monthColumns: Column<RootCauseRow>[] = [
  { key: 'month', header: 'Month' },
  { key: 'region', header: 'Region' },
  { key: 'estimated_read_rate', header: 'Estimated reads', align: 'right', cell: (r) => rateBar(r.estimated_read_rate) },
  { key: 'smart_meter_penetration', header: 'Smart meters', align: 'right', cell: (r) => pct(r.smart_meter_penetration) },
  { key: 'billing_exceptions_per_1000', header: 'Billing exceptions / 1,000', align: 'right' },
  { key: 'complaints', header: 'Complaints', align: 'right' },
  { key: 'billing_metering_per_1000', header: 'Billing and metering / 1,000', align: 'right' },
]

const clusterColumns: Column<ClusterRow>[] = [
  { key: 'region', header: 'Region' },
  { key: 'category', header: 'Category' },
  { key: 'open_cases', header: 'Open', align: 'right' },
  { key: 'breached_cases', header: 'Past target', align: 'right', cell: (r) => <span className="text-red-600">{r.breached_cases}</span> },
  { key: 'region_estimated_read_rate', header: 'Region estimated reads', align: 'right', cell: (r) => pct(r.region_estimated_read_rate) },
  {
    key: 'estimation_driven',
    header: 'Likely cause',
    cell: (r) => (r.estimation_driven ? <Badge tone="purple">Estimated readings</Badge> : <span className="text-gray-300">-</span>),
  },
]

export default function RootCause() {
  return (
    <>
      <PageHeader
        title="Root cause"
        description="Where complaints start: regions with more estimated readings raise more billing and metering complaints."
      />

      <StatRow>
        <StatCard label="Estimated reads, Barrowdale" value="62%" hint="No smart meters" />
        <StatCard label="Estimated reads, other regions" value="16-26%" hint="81% smart meters" />
        <StatCard label="Correlation" value="0.66" hint="Estimated-read rate against billing complaints" />
        <StatCard label="Open, estimation driven" value="228" hint="Barrowdale and Dunmoor" />
      </StatRow>

      <FilterBar>
        <Select label="Region" options={REGIONS} />
        <Select label="From month" options={['2026-01', '2026-06', '2026-08']} />
        <Select label="To month" options={['2026-08', '2026-09']} />
        <ToggleChip label="High estimates only (40%+)" />
      </FilterBar>

      <Card>
        <CardTitle title="Region and month" hint="Estimated-read rate next to billing and metering complaints" />
        <DataTable columns={monthColumns} rows={rootCause} rowKey={(r) => `${r.month}-${r.region}`} pageSize={10} total={144} />
      </Card>

      <Card>
        <CardTitle title="Open complaints by region and category" hint="Clusters in today's backlog, next to the region's meter data" />
        <div className="mb-4 flex flex-wrap gap-3">
          <Select label="Category" options={CATEGORIES} />
          <div className="flex items-end">
            <ToggleChip label="Estimation driven only" />
          </div>
        </div>
        <DataTable columns={clusterColumns} rows={clusters} rowKey={(r) => `${r.region}-${r.category}`} pageSize={10} total={54} />
      </Card>
    </>
  )
}
