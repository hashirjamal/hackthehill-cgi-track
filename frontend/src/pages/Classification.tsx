import Card, { CardTitle } from '../components/Card'
import { FilterBar, SegmentedControl, Select } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import StatCard, { StatRow } from '../components/StatCard'
import { agentResults, classificationSummary } from '../mock'
import { pct } from '../lib/format'
import type { AgentResultRow, ClassificationSummaryRow } from '../types'

const agentColumns: Column<AgentResultRow>[] = [
  { key: 'name', header: 'AI agent' },
  { key: 'classified', header: 'Classified', align: 'right' },
  { key: 'fast_lane', header: 'Quick lane', align: 'right' },
  { key: 'runs', header: 'Runs', align: 'right' },
  { key: 'drafts_pending', header: 'Drafts waiting', align: 'right' },
  { key: 'drafts_approved', header: 'Drafts approved', align: 'right' },
]

const summaryColumns: Column<ClassificationSummaryRow>[] = [
  { key: 'group_name', header: 'Group' },
  { key: 'classifications', header: 'Cases', align: 'right' },
  { key: 'share_of_total', header: 'Share', align: 'right', cell: (r) => pct(r.share_of_total, 1) },
  { key: 'avg_group_confidence', header: 'Avg confidence', align: 'right', cell: (r) => pct(r.avg_group_confidence) },
  { key: 'data_fallbacks', header: 'Used the data category', align: 'right' },
]

export default function Classification() {
  return (
    <>
      <PageHeader
        title="Classification"
        description="How the classifier sorted complaints, and what each AI agent has done with them."
      />

      <StatRow>
        <StatCard label="Classified" value="54" hint="Current classifications" />
        <StatCard label="Laya was confident" value="21" hint="Top group at 60% or more" />
        <StatCard label="Used the data category" value="33" hint="Laya was under 60% sure" />
        <StatCard label="Drafts waiting" value="0" hint="AI agents not connected yet" />
      </StatRow>

      <Card>
        <CardTitle title="AI agents" hint="One agent for each group" />
        <DataTable columns={agentColumns} rows={agentResults} rowKey={(r) => r.agent_id} pageSize={10} />
      </Card>

      <FilterBar>
        <SegmentedControl label="Group results by" options={['Group', 'Lane', 'Team', 'Priority', 'Source']} />
        <Select label="Group" options={agentResults.map((a) => a.name)} />
        <Select label="Classified" options={['Current only', 'Including history']} />
      </FilterBar>

      <Card>
        <CardTitle title="Classification results" hint="Counts, confidence and how often the data category was used instead" />
        <DataTable columns={summaryColumns} rows={classificationSummary} rowKey={(r) => r.group_name} pageSize={10} />
      </Card>
    </>
  )
}
