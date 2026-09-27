import { X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAccountHistory, useAccountsTotal } from '../api/reports'
import Badge, { PriorityBadge } from '../components/Badge'
import Card from '../components/Card'
import { DateField, FilterBar, SearchField, Select, ToggleChip } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { CATEGORIES, STATUSES } from '../constants'
import { useListParams } from '../hooks/useListParams'
import { num, pct, shortDate } from '../lib/format'
import { serverTable } from '../lib/serverTable'
import type { AccountHistoryRow } from '../types'

const SUMMARY = 'the summary numbers' // one toast if they all fail

const columns: Column<AccountHistoryRow>[] = [
  { key: 'account_id', header: 'Account', sortKey: 'account_id' },
  {
    key: 'complaint_id',
    header: 'Complaint',
    sortKey: 'complaint_id',
    cell: (r) => (
      <Link to={`/cases/${r.complaint_id}`} className="font-medium text-brand hover:underline">
        {r.complaint_id}
      </Link>
    ),
  },
  { key: 'date_opened', header: 'Opened', sortKey: 'date_opened', cell: (r) => shortDate(r.date_opened) },
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
  { key: 'priority', header: 'Priority', sortKey: 'priority', cell: (r) => <PriorityBadge priority={r.priority} /> },
  { key: 'status', header: 'Status', sortKey: 'status' },
  { key: 'complaint_seq', header: 'Nth complaint', align: 'right', sortKey: 'complaint_seq', cell: (r) => `${r.complaint_seq} of ${r.complaints_on_account}` },
  {
    key: 'days_since_previous',
    header: 'Days since previous',
    align: 'right',
    sortKey: 'days_since_previous',
    cell: (r) => r.days_since_previous ?? <span className="text-gray-400">-</span>,
  },
  { key: 'is_repeat', header: 'Repeat', sortKey: 'is_repeat', cell: (r) => (r.is_repeat ? <Badge tone="amber">Repeat</Badge> : <span className="text-gray-400">First</span>) },
]

export default function Accounts() {
  const list = useListParams({ pageSize: 10 })
  const f = list.filters

  // The page is about repeat contact, so it starts with the accounts that have more than one complaint.
  // Looking at one account (from a case page) shows all of its complaints instead.
  const repeatOnly = f.repeat_accounts_only !== 'false' && !f.account_id
  const query = useAccountHistory({ ...list.params, repeat_accounts_only: repeatOnly ? true : undefined })

  const accounts = useAccountsTotal({ is_repeat: false }, SUMMARY)
  const repeatAccounts = useAccountsTotal({ is_repeat: false, repeat_accounts_only: true }, SUMMARY)
  const repeats = useAccountsTotal({ is_repeat: true }, SUMMARY)
  const quick = useAccountsTotal({ is_repeat: true, days_since_previous_max: 7 }, SUMMARY)

  return (
    <>
      <PageHeader title="Accounts" description="Every complaint per account, in order, so repeat contact is easy to spot." />

      <StatRow>
        <StatCard label="Accounts with complaints" value={num(accounts.data ?? 0)} loading={accounts.isPending} error={accounts.isError} />
        <StatCard
          label="Accounts with repeats"
          value={num(repeatAccounts.data ?? 0)}
          hint={accounts.data ? `${pct((repeatAccounts.data ?? 0) / accounts.data, 1)} of accounts` : undefined}
          loading={repeatAccounts.isPending}
          error={repeatAccounts.isError}
        />
        <StatCard label="Repeat complaints" value={num(repeats.data ?? 0)} loading={repeats.isPending} error={repeats.isError} />
        <StatCard label="Repeats within 7 days" value={num(quick.data ?? 0)} hint="Raised again within a week" loading={quick.isPending} error={quick.isError} />
      </StatRow>

      <FilterBar onClear={list.hasFilters ? list.clearFilters : undefined}>
        {f.account_id && (
          <span className="inline-flex items-center gap-2 rounded-full bg-brand-soft py-2 pr-2 pl-4 text-sm font-medium text-brand">
            Account {f.account_id}
            <button type="button" aria-label="Show all accounts" onClick={() => list.setFilter('account_id', undefined)} className="rounded-full p-1 hover:bg-white/60">
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        )}
        <SearchField placeholder="Account or complaint id" value={f.q} onChange={(v) => list.setFilter('q', v)} />
        <Select label="Category" options={CATEGORIES} value={f.category} onChange={(v) => list.setFilter('category', v)} />
        <Select label="Status" options={STATUSES} value={f.status} onChange={(v) => list.setFilter('status', v)} />
        <DateField label="Opened from" value={f.opened_from} onChange={(v) => list.setFilter('opened_from', v)} />
        <DateField label="Opened to" value={f.opened_to} onChange={(v) => list.setFilter('opened_to', v)} />
        <ToggleChip
          label="Repeat accounts only"
          on={repeatOnly}
          onChange={(on) => list.setFilter('repeat_accounts_only', on ? undefined : 'false')}
        />
        <ToggleChip label="Repeat complaints only" on={f.is_repeat === 'true'} onChange={(on) => list.setToggle('is_repeat', on)} />
      </FilterBar>

      <Card>
        <DataTable columns={columns} rows={query.data?.items ?? []} rowKey={(r) => r.complaint_id} server={serverTable(list, query)} />
      </Card>
    </>
  )
}
