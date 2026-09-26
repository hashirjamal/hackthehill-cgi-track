import { Link } from 'react-router-dom'
import Badge from '../components/Badge'
import Card from '../components/Card'
import { DateField, FilterBar, SearchField, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, accountHistory } from '../mock'
import type { AccountHistoryRow } from '../types'

const columns: Column<AccountHistoryRow>[] = [
  { key: 'account_id', header: 'Account' },
  {
    key: 'complaint_id',
    header: 'Complaint',
    cell: (r) => (
      <Link to={`/cases/${r.complaint_id}`} className="font-medium text-brand hover:underline">
        {r.complaint_id}
      </Link>
    ),
  },
  { key: 'date_opened', header: 'Opened' },
  { key: 'category', header: 'Category' },
  { key: 'status', header: 'Status' },
  { key: 'complaint_seq', header: 'Nth complaint', align: 'right', cell: (r) => `${r.complaint_seq} of ${r.complaints_on_account}` },
  {
    key: 'days_since_previous',
    header: 'Days since previous',
    align: 'right',
    cell: (r) => r.days_since_previous ?? <span className="text-gray-300">-</span>,
  },
  { key: 'is_repeat', header: 'Repeat', cell: (r) => (r.is_repeat ? <Badge tone="amber">Repeat</Badge> : <span className="text-gray-300">First</span>) },
]

export default function Accounts() {
  return (
    <>
      <PageHeader title="Accounts" description="Every complaint per account, in order, so repeat contact is easy to spot." />

      <StatRow>
        <StatCard label="Accounts with complaints" value="25,074" />
        <StatCard label="Accounts with repeats" value="337" hint="1.3% of accounts" />
        <StatCard label="Repeat complaints" value="342" />
        <StatCard label="Repeats within 7 days" value="7" />
      </StatRow>

      <FilterBar>
        <SearchField placeholder="Account or complaint id" />
        <Select label="Category" options={CATEGORIES} />
        <Select label="Status" options={['Open', 'Closed', 'Closed - reopened']} />
        <DateField label="Opened from" />
        <DateField label="Opened to" />
        <ToggleChip label="Repeat accounts only" defaultOn />
        <ToggleChip label="Repeat complaints only" />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={accountHistory} rowKey={(r) => r.complaint_id} pageSize={10} total={679} />
      </Card>
    </>
  )
}
