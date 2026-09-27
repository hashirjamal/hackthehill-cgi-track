import { useProfiles } from '../api/reports'
import Card from '../components/Card'
import { FilterBar, Select } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import { CATEGORIES, REGIONS, SOURCE_SYSTEMS } from '../constants'
import { useListParams } from '../hooks/useListParams'
import { num, pct } from '../lib/format'
import { serverTable } from '../lib/serverTable'
import type { ProfileRow } from '../types'

const RESOLUTIONS = [
  'Bill corrected and re-issued',
  'Refund or credit applied',
  'Meter visit required',
  'Field repair required',
  'Payment plan amended',
  'Appointment rebooked by agent',
  'Information provided only',
  'Apology and manual process fix',
  'Compensation payment issued',
  'No action - explained to customer',
]
const MIN_CASES = [
  { value: '50', label: '50 or more' },
  { value: '100', label: '100 or more' },
  { value: '200', label: '200 or more' },
]

const columns: Column<ProfileRow>[] = [
  { key: 'category', header: 'Category', sortKey: 'category' },
  { key: 'region', header: 'Region', sortKey: 'region' },
  { key: 'source_system', header: 'Source system', sortKey: 'source_system' },
  { key: 'n', header: 'Closed cases', align: 'right', sortKey: 'n', cell: (r) => num(r.n) },
  { key: 'avg_days', header: 'Avg days', align: 'right', sortKey: 'avg_days' },
  { key: 'info_only_share', header: 'Info only', align: 'right', sortKey: 'info_only_share', cell: (r) => pct(r.info_only_share) },
  { key: 'transfer_rate', header: 'Transferred', align: 'right', sortKey: 'transfer_rate', cell: (r) => pct(r.transfer_rate) },
  { key: 'reopen_rate', header: 'Reopened', align: 'right', sortKey: 'reopen_rate', cell: (r) => pct(r.reopen_rate) },
  { key: 'breach_rate', header: 'Breached', align: 'right', sortKey: 'breach_rate', cell: (r) => pct(r.breach_rate) },
  { key: 'top_resolution', header: 'Usually ends with', sortKey: 'top_resolution' },
]

export default function Profiles() {
  const list = useListParams({ pageSize: 10 })
  const query = useProfiles(list.params)
  const f = list.filters

  return (
    <>
      <PageHeader title="Case profiles" description="How closed cases of each type ended: the patterns the AI agents work from." />

      <FilterBar onClear={list.hasFilters ? list.clearFilters : undefined}>
        <Select label="Category" options={CATEGORIES} value={f.category} onChange={(v) => list.setFilter('category', v)} />
        <Select label="Region" options={REGIONS} value={f.region} onChange={(v) => list.setFilter('region', v)} />
        <Select label="Source system" options={SOURCE_SYSTEMS} value={f.source_system} onChange={(v) => list.setFilter('source_system', v)} />
        <Select label="Usually ends with" options={RESOLUTIONS} value={f.top_resolution} onChange={(v) => list.setFilter('top_resolution', v)} />
        <Select label="Closed cases" options={MIN_CASES} value={f.n_min} onChange={(v) => list.setFilter('n_min', v)} allLabel="Any number" />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={query.data?.items ?? []} rowKey={(r) => `${r.category}-${r.region}-${r.source_system}`} server={serverTable(list, query)} />
      </Card>
    </>
  )
}
