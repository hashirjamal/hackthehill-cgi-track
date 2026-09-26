import { ArrowLeft, Bot } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import Badge, { LaneBadge, PriorityBadge } from '../components/Badge'
import { ShareBar } from '../components/BarChart'
import Card, { CardTitle } from '../components/Card'
import DataTable, { type Column } from '../components/DataTable'
import PageHeader from '../components/PageHeader'
import { accountHistory } from '../mock'
import type { AccountHistoryRow } from '../types'

// One sample case. When the API is connected this page loads GET /reports/cases/{id}.
const sample = {
  account_id: 'ACC-943644',
  status: 'Open',
  category: 'Billing - estimated read',
  region: 'Barrowdale',
  channel: 'Phone',
  source_system: 'SYS-05',
  opened: '16 Jun 2026',
  sla_days: 20,
  days_open: 106,
  transferred: false,
  priority: 'P3' as const,
  classified_priority: 'P2' as const,
}

const meter = [
  { month: 'Sep', rate: 0.62 },
  { month: 'Aug', rate: 0.63 },
  { month: 'Jul', rate: 0.6 },
  { month: 'Jun', rate: 0.62 },
  { month: 'May', rate: 0.64 },
  { month: 'Apr', rate: 0.61 },
]

const mix = [
  { label: 'Bill corrected and re-issued', share: 0.415 },
  { label: 'Meter visit required', share: 0.378 },
  { label: 'Information provided only', share: 0.129 },
  { label: 'No action - explained', share: 0.078 },
]

const historyColumns: Column<AccountHistoryRow>[] = [
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
  { key: 'is_repeat', header: 'Repeat', cell: (r) => (r.is_repeat ? <Badge tone="amber">Repeat</Badge> : <span className="text-gray-300">First</span>) },
]

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-800">{children}</dd>
    </div>
  )
}

export default function CaseDetail() {
  const { id } = useParams()
  return (
    <>
      <PageHeader
        title={id ?? 'Case'}
        description="Everything known about one complaint. This is a sample case until the page is connected to the API."
        actions={
          <Link to="/worklist" className="inline-flex items-center gap-1.5 rounded-xl bg-gray-100 px-3 py-2 text-sm text-gray-600 hover:bg-gray-200">
            <ArrowLeft className="h-4 w-4" /> Worklist
          </Link>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="flex flex-col gap-4 xl:col-span-2">
          <Card>
            <CardTitle title="Case" />
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              <Fact label="Category">{sample.category}</Fact>
              <Fact label="Region">{sample.region}</Fact>
              <Fact label="Account">{sample.account_id}</Fact>
              <Fact label="Status"><Badge tone="brand">{sample.status}</Badge></Fact>
              <Fact label="Channel">{sample.channel}</Fact>
              <Fact label="Source system">{sample.source_system}</Fact>
              <Fact label="Opened">{sample.opened}</Fact>
              <Fact label="SLA target">{sample.sla_days} days</Fact>
              <Fact label="Days open"><span className="font-medium text-red-600">{sample.days_open}</span> ({sample.days_open - sample.sla_days} overdue)</Fact>
            </dl>
          </Card>

          <Card>
            <CardTitle title="Classification" hint="What the classifier decided, and why" />
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              <Fact label="Group">Billing <span className="text-xs text-gray-500">from Laya, 95% sure</span></Fact>
              <Fact label="Subcategory">Billing - estimated read</Fact>
              <Fact label="Routed to">Metering team</Fact>
              <Fact label="Priority">
                <PriorityBadge priority={sample.classified_priority} />
                <div className="mt-1 text-xs font-normal text-gray-500">was {sample.priority}, raised by deadline risk</div>
              </Fact>
              <Fact label="Lane"><LaneBadge lane="standard" /></Fact>
              <Fact label="Likely cause">Estimated reading</Fact>
            </dl>
          </Card>

          <Card>
            <CardTitle title="Account history" hint="Every complaint on this account, oldest first" />
            <DataTable columns={historyColumns} rows={accountHistory.slice(0, 3)} rowKey={(r) => r.complaint_id} pageSize={5} />
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <CardTitle title="Draft reply and actions" hint="From the AI agent for this group" />
            <div className="flex flex-col items-center gap-2 rounded-xl bg-gray-100 px-4 py-8 text-center">
              <Bot className="h-6 w-6 text-brand" />
              <p className="text-sm text-gray-600">No draft yet</p>
              <p className="text-xs text-gray-400">The AI agents are not connected yet. Drafts and action items will show here for staff to approve.</p>
            </div>
          </Card>

          <Card>
            <CardTitle title="Region meter picture" hint="Barrowdale, estimated-read rate by month" />
            <div className="flex flex-col gap-3">
              {meter.map((m) => (
                <ShareBar key={m.month} label={m.month} share={m.rate} />
              ))}
            </div>
            <p className="mt-4 text-xs text-gray-400">No smart meters in this region. 25 billing exceptions per 1,000 accounts.</p>
          </Card>

          <Card>
            <CardTitle title="How similar cases ended" hint="4,485 closed cases of this category" />
            <div className="flex flex-col gap-3">
              {mix.map((m) => (
                <ShareBar key={m.label} label={m.label} share={m.share} />
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
