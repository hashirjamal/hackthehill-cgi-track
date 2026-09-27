import { useMemo } from 'react'
import { useAgentResults, useClassificationSummary } from '../api/reports'
import Badge, { LaneBadge, PriorityBadge } from '../components/Badge'
import Card, { CardTitle } from '../components/Card'
import { FilterBar, SegmentedControl, Select } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { useListParams } from '../hooks/useListParams'
import { num, pct } from '../lib/format'
import { serverTable } from '../lib/serverTable'
import type { AgentResultRow, ClassificationSummaryRow, Priority } from '../types'

const SUMMARY = 'the summary numbers' // one toast if they all fail

const GROUPS = [
  { value: 'group_name', label: 'Group' },
  { value: 'lane', label: 'Lane' },
  { value: 'routed_team', label: 'Team' },
  { value: 'priority', label: 'Priority' },
  { value: 'group_source', label: 'Answered by' },
]
const GROUP_NAMES = ['Billing', 'Metering', 'Field services', 'Customer support', 'General']
const VIEWS = [
  { value: 'current', label: 'Current only' },
  { value: 'all', label: 'Including history' },
]

const agentColumns: Column<AgentResultRow>[] = [
  { key: 'name', header: 'AI agent', sortKey: 'name' },
  { key: 'classified', header: 'Classified', align: 'right', sortKey: 'classified' },
  { key: 'fast_lane', header: 'Quick lane', align: 'right', sortKey: 'fast_lane' },
  { key: 'runs', header: 'Runs', align: 'right', sortKey: 'runs' },
  { key: 'runs_failed', header: 'Failed', align: 'right', sortKey: 'runs_failed' },
  { key: 'drafts_pending', header: 'Drafts waiting', align: 'right', sortKey: 'drafts_pending' },
  { key: 'drafts_approved', header: 'Drafts approved', align: 'right', sortKey: 'drafts_approved' },
]

/** How a group's value is drawn: a badge for lane, priority and who answered, plain text otherwise. */
function groupCell(group: string, row: ClassificationSummaryRow) {
  const value = row[group]
  if (value === null || value === undefined) return <span className="text-gray-400">Not set</span>
  if (group === 'lane') return <LaneBadge lane={String(value)} />
  if (group === 'priority') return <PriorityBadge priority={value as Priority} />
  if (group === 'group_source') return <Badge tone={value === 'laya' ? 'brand' : 'gray'}>{value === 'laya' ? 'Laya' : 'Data category'}</Badge>
  return String(value)
}

export default function Classification() {
  // Two tables with their own paging, sorting and filters in the URL. The results table's keys start with "s_".
  const agents = useListParams({ pageSize: 10, others: ['s_'] })
  const results = useListParams({ pageSize: 10, prefix: 's_' })
  const rf = results.filters
  const group = GROUPS.some((g) => g.value === rf.group_by) ? rf.group_by : 'group_name'
  const current = rf.view !== 'all'

  const agentsQuery = useAgentResults(agents.params)
  const summary = useClassificationSummary({
    group_by: group,
    current_only: current,
    group_name: rf.group_name,
    page: results.page,
    page_size: results.pageSize,
    sort: results.sort,
  })

  // The stat cards look at everything, whatever the tables are set to.
  const bySource = useClassificationSummary({ group_by: 'group_source', page_size: 10 }, SUMMARY)
  const allAgents = useAgentResults({ page_size: 50 }, SUMMARY)
  const source = (name: string) => (bySource.data?.items ?? []).find((r) => r.group_source === name)?.classifications ?? 0
  const classified = source('laya') + source('data')
  const waiting = (allAgents.data?.items ?? []).reduce((s, a) => s + a.drafts_pending, 0)

  // The table is drawn for the grouping of the rows on screen, so the columns do not switch before their rows arrive.
  const shownGroup = summary.data?.group_by?.[0] ?? group
  const summaryColumns = useMemo<Column<ClassificationSummaryRow>[]>(
    () => [
      { key: shownGroup, header: GROUPS.find((g) => g.value === shownGroup)?.label ?? shownGroup, sortKey: shownGroup, cell: (r) => groupCell(shownGroup, r) },
      { key: 'classifications', header: 'Cases', align: 'right', sortKey: 'classifications', cell: (r) => num(r.classifications) },
      { key: 'share_of_total', header: 'Share', align: 'right', sortKey: 'share_of_total', cell: (r) => pct(r.share_of_total, 1) },
      {
        key: 'avg_group_confidence',
        header: 'Avg confidence',
        align: 'right',
        sortKey: 'avg_group_confidence',
        cell: (r) => (r.avg_group_confidence === null ? '-' : pct(r.avg_group_confidence)),
      },
      { key: 'data_fallbacks', header: 'Used the data category', align: 'right', sortKey: 'data_fallbacks' },
      {
        key: 'group_match_rate',
        header: 'Laya agreed with the data',
        align: 'right',
        sortKey: 'group_match_rate',
        cell: (r) => (r.group_match_rate === null ? '-' : pct(r.group_match_rate)),
      },
    ],
    [shownGroup],
  )

  return (
    <>
      <PageHeader title="Classification" description="How the classifier sorted complaints, and what each AI agent has done with them." />

      <StatRow>
        <StatCard label="Classified" value={num(classified)} hint="Current classifications" loading={bySource.isPending} error={bySource.isError} />
        <StatCard label="Laya was confident" value={num(source('laya'))} hint="Top group at 60% or more" loading={bySource.isPending} error={bySource.isError} />
        <StatCard label="Used the data category" value={num(source('data'))} hint="Laya was under 60% sure" loading={bySource.isPending} error={bySource.isError} />
        <StatCard label="Drafts waiting" value={num(waiting)} hint={waiting === 0 ? 'None yet' : 'Waiting for staff'} loading={allAgents.isPending} error={allAgents.isError} />
      </StatRow>

      <Card>
        <CardTitle title="AI agents" hint="One agent for each group" />
        <DataTable columns={agentColumns} rows={agentsQuery.data?.items ?? []} rowKey={(r) => r.agent_id} server={serverTable(agents, agentsQuery)} />
      </Card>

      <FilterBar onClear={results.hasFilters ? results.clearFilters : undefined}>
        <SegmentedControl
          label="Group results by"
          options={GROUPS}
          value={group}
          onChange={(v) => results.setMany({ group_by: v === 'group_name' ? undefined : v, sort: undefined })}
        />
        <Select label="Group" options={GROUP_NAMES} value={rf.group_name} onChange={(v) => results.setFilter('group_name', v)} />
        <Select label="Classifications" options={VIEWS.slice(1)} value={rf.view} onChange={(v) => results.setFilter('view', v)} allLabel="Current only" />
      </FilterBar>

      <Card>
        <CardTitle title="Classification results" hint="Counts, confidence and how often the data category was used instead" />
        <DataTable
          columns={summaryColumns}
          rows={summary.data?.items ?? []}
          rowKey={(r) => String(r[shownGroup] ?? 'none')}
          server={serverTable(results, summary, 'Nothing has been classified yet. Use "Classify" on the Worklist.')}
        />
      </Card>
    </>
  )
}
