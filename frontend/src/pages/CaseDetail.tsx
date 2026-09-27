import { ArrowLeft, Loader2, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useCaseContext, useClassify } from '../api/reports'
import Badge, { LaneBadge, PriorityBadge } from '../components/Badge'
import AgentPanel from '../components/AgentPanel'
import { ShareBar } from '../components/BarChart'
import Card, { CardTitle } from '../components/Card'
import { Button } from '../components/Controls'
import DataTable, { type Column } from '../components/DataTable'
import ErrorState from '../components/ErrorState'
import PageHeader from '../components/PageHeader'
import Skeleton from '../components/Skeleton'
import { humanize, num, pct, shortDate } from '../lib/format'
import type { AccountCase, CaseContext } from '../types'

const monthName = (m: string) => new Date(`${m}-01T00:00:00`).toLocaleDateString('en-GB', { month: 'short', year: '2-digit' })

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-800">{children}</dd>
    </div>
  )
}

const historyColumns: Column<AccountCase>[] = [
  {
    key: 'complaint_id',
    header: 'Complaint',
    cell: (r) => (
      <Link to={`/cases/${r.complaint_id}`} className="font-medium text-brand hover:underline">
        {r.complaint_id}
      </Link>
    ),
  },
  { key: 'date_opened', header: 'Opened', cell: (r) => shortDate(r.date_opened) },
  { key: 'category', header: 'Category' },
  { key: 'status', header: 'Status' },
  { key: 'is_repeat', header: 'Repeat', cell: (r) => (r.is_repeat ? <Badge tone="amber">Repeat</Badge> : <span className="text-gray-400">First</span>) },
]

/** The page's shape while it loads, so nothing jumps when the data arrives. */
function DetailSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-3" aria-busy>
      <div className="flex flex-col gap-4 xl:col-span-2">
        {[180, 200, 220].map((h) => (
          <Card key={h}>
            <Skeleton className="mb-4 h-5 w-32" />
            <Skeleton className="w-full" style={{ height: h - 60 }} />
          </Card>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        {[150, 260, 220].map((h) => (
          <Card key={h}>
            <Skeleton className="mb-4 h-5 w-40" />
            <Skeleton className="w-full" style={{ height: h - 60 }} />
          </Card>
        ))}
      </div>
    </div>
  )
}

function Body({ data }: { data: CaseContext }) {
  const c = data.case
  const cl = data.classification
  const classify = useClassify()
  const mix = data.resolution_mix.filter((m) => m.resolution_action)

  const runClassify = () =>
    classify.mutate([
      {
        complaint_id: c.complaint_id,
        category: c.category,
        priority: c.priority,
        sla_days: c.sla_days,
        channel: c.channel,
        region: c.region,
        source_system: c.source_system,
        date_opened: c.date_opened,
        account_id: c.account_id,
        transferred_between_systems: c.transferred_between_systems,
      },
    ])

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <div className="flex flex-col gap-4 xl:col-span-2">
        <Card>
          <CardTitle title="Case" />
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
            <Fact label="Category">{c.category}</Fact>
            <Fact label="Region">{c.region}</Fact>
            <Fact label="Account">
              <Link to={`/accounts?account_id=${encodeURIComponent(c.account_id)}`} className="text-brand hover:underline">
                {c.account_id}
              </Link>
            </Fact>
            <Fact label="Status">
              <Badge tone={c.status === 'Open' ? 'brand' : c.status === 'Closed' ? 'gray' : 'amber'}>{c.status}</Badge>
            </Fact>
            <Fact label="Channel">{c.channel}</Fact>
            <Fact label="Source system">{c.source_system}</Fact>
            <Fact label="Opened">{shortDate(c.date_opened)}</Fact>
            <Fact label="SLA target">{c.sla_days} days</Fact>
            <Fact label={c.status === 'Open' ? 'Days open' : 'Days to close'}>
              <span className={c.breached_live ? 'font-medium text-red-600' : undefined}>{c.days_open}</span>{' '}
              <span className="text-gray-500">
                ({c.days_overdue > 0 ? `${c.days_overdue} over the target` : `${Math.abs(c.days_overdue)} inside the target`})
              </span>
            </Fact>
            <Fact label="Transferred between systems">{c.transferred_between_systems ? 'Yes' : 'No'}</Fact>
            {c.date_closed && <Fact label="Closed">{shortDate(c.date_closed)}</Fact>}
            {c.resolution_action && <Fact label="Resolution">{c.resolution_action}</Fact>}
            {c.bill_correction_value !== null && <Fact label="Bill correction">{num(c.bill_correction_value)}</Fact>}
          </dl>
        </Card>

        <Card>
          <CardTitle title="Classification" hint="What the classifier decided, and why" />
          {cl ? (
            <div className="flex flex-col gap-5">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                <Fact label="Group">
                  {cl.group_name}
                  <div className="mt-0.5 text-xs text-gray-500">
                    {cl.group_source === 'laya'
                      ? `From Laya, ${pct(cl.group_confidence ?? 0)} sure`
                      : `Laya was only ${pct(cl.group_confidence ?? 0)} sure (${cl.laya_group}), so the recorded category was used`}
                  </div>
                </Fact>
                <Fact label="Subcategory">{cl.subcategory ?? '-'}</Fact>
                <Fact label="Routed to">{cl.routed_team}</Fact>
                <Fact label="Priority">
                  <PriorityBadge priority={cl.priority} />
                  {cl.priority !== cl.base_priority && <div className="mt-1 text-xs text-gray-500">was {cl.base_priority}, raised by the flags below</div>}
                </Fact>
                <Fact label="Lane">
                  <LaneBadge lane={cl.lane} />
                </Fact>
                <Fact label="Likely cause">{cl.likely_cause ? humanize(cl.likely_cause) : '-'}</Fact>
              </dl>
              {cl.flags.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium text-gray-500">Flags that fired</p>
                  <ul className="flex flex-col gap-1.5">
                    {cl.flags.map((flag) => (
                      <li key={flag.name} className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
                        <Badge tone="amber">{humanize(flag.name)}</Badge>
                        {flag.reason && <span className="text-gray-500">{flag.reason}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-xl bg-gray-100 px-4 py-8 text-center">
              <p className="text-sm text-gray-600">This case has not been classified yet.</p>
              <Button onClick={runClassify} disabled={classify.isPending}>
                <span className="inline-flex items-center gap-2">
                  {classify.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {classify.isPending ? 'Classifying…' : 'Classify this case'}
                </span>
              </Button>
            </div>
          )}
        </Card>

        <Card>
          <CardTitle
            title="Account history"
            hint={`${num(data.account_complaints_total)} ${data.account_complaints_total === 1 ? 'complaint' : 'complaints'} on this account, oldest first`}
          />
          <DataTable columns={historyColumns} rows={data.account_history} rowKey={(r) => r.complaint_id} pageSize={5} />
        </Card>
      </div>

      <div className="flex flex-col gap-4">
        <AgentPanel data={data} />

        <Card>
          <CardTitle title="Region meter picture" hint={`${c.region}, estimated-read rate by month`} />
          {data.region_meter.length === 0 ? (
            <p className="text-sm text-gray-500">No meter data for this region.</p>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {data.region_meter.map((m) => (
                  <ShareBar key={m.month} label={monthName(m.month)} share={m.estimated_read_rate} />
                ))}
              </div>
              <p className="mt-4 text-sm text-gray-500">
                {data.region_meter[0].smart_meter_penetration === 0 ? 'No smart meters in this region. ' : `${pct(data.region_meter[0].smart_meter_penetration)} smart meters. `}
                {data.region_meter[0].billing_exceptions_per_1000} billing exceptions per 1,000 accounts.
              </p>
            </>
          )}
        </Card>

        <Card>
          <CardTitle
            title="How similar cases ended"
            hint={data.category_profile ? `${num(data.category_profile.n)} closed cases of this category` : 'No closed cases of this category'}
          />
          {mix.length > 0 ? (
            <div className="flex flex-col gap-3">
              {mix.map((m) => (
                <ShareBar key={m.resolution_action} label={m.resolution_action} share={m.share} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Nothing to compare with yet.</p>
          )}
          {data.category_profile?.avg_days != null && (
            <p className="mt-4 text-sm text-gray-500">
              They took {data.category_profile.avg_days} days on average, and {pct(data.category_profile.transfer_rate ?? 0)} were transferred between systems.
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}

export default function CaseDetail() {
  const { id = '' } = useParams()
  const query = useCaseContext(id)
  const notFound = query.error instanceof ApiError && query.error.status === 404

  return (
    <>
      <PageHeader
        title={id}
        description="Everything known about one complaint: the case, how it was classified, the region's meter data and the account's history."
        actions={
          <Link to="/cases" className="inline-flex items-center gap-1.5 rounded-xl bg-gray-100 px-3 py-2 text-sm text-gray-600 hover:bg-gray-200">
            <ArrowLeft className="h-4 w-4" /> All cases
          </Link>
        }
      />
      {query.isPending && <DetailSkeleton />}
      {query.isError && (
        <Card>
          <ErrorState title={notFound ? 'Complaint not found' : "Couldn't load this case"} error={query.error} onRetry={() => void query.refetch()}>
            <Link to="/cases" className="text-sm font-medium text-brand hover:underline">
              Search the cases
            </Link>
          </ErrorState>
        </Card>
      )}
      {query.data && <Body data={query.data} />}
    </>
  )
}
