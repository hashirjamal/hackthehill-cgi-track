import Card from '../components/Card'
import { FilterBar, Select } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import { CATEGORIES, REGIONS, profiles } from '../mock'
import { pct } from '../lib/format'
import type { ProfileRow } from '../types'

const columns: Column<ProfileRow>[] = [
  { key: 'category', header: 'Category' },
  { key: 'region', header: 'Region' },
  { key: 'source_system', header: 'Source system' },
  { key: 'n', header: 'Closed cases', align: 'right' },
  { key: 'avg_days', header: 'Avg days', align: 'right' },
  { key: 'info_only_share', header: 'Info only', align: 'right', cell: (r) => pct(r.info_only_share) },
  { key: 'transfer_rate', header: 'Transferred', align: 'right', cell: (r) => pct(r.transfer_rate) },
  { key: 'reopen_rate', header: 'Reopened', align: 'right', cell: (r) => pct(r.reopen_rate) },
  { key: 'top_resolution', header: 'Usually ends with' },
]

export default function Profiles() {
  return (
    <>
      <PageHeader
        title="Case profiles"
        description="How closed cases of each type ended: the patterns the AI agents work from."
      />

      <FilterBar>
        <Select label="Category" options={CATEGORIES} />
        <Select label="Region" options={REGIONS} />
        <Select label="Source system" options={['SYS-01', 'SYS-03', 'SYS-04', 'SYS-05']} />
        <Select label="Usually ends with" options={['Bill corrected and re-issued', 'Meter visit required', 'Field repair required', 'Information provided only']} />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={profiles} rowKey={(r) => `${r.category}-${r.region}-${r.source_system}`} pageSize={10} total={216} />
      </Card>
    </>
  )
}
