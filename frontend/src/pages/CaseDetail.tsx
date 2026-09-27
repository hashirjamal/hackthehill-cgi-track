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
import Skeleton from '../components/Skeleton'
import { cn } from '../lib/cn'
import { humanize, num, pct, shortDate } from '../lib/format'
import type { AccountCase, CaseContext } from '../types'

const monthName = (m: string) => new Date(`${m}-01T00:00:00`).toLocaleDateString('en-GB', { month: 'short', year: '2-digit' })

/** One label/value row in the side rail: label left, value right, a hairline between rows. */
function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line/70 py-2 last:border-0">
      <dt className="shrink-0 text-xs text-gray-500">{label}</dt>
      <dd className="min-w-0 text-right text-sm text-ink">{children}</dd>
    </div>
  )
}

const statusTone = (status: string) => (status === 'Open' ? 'brand' : status === 'Closed' ? 'gray' : 'amber')

/** The top of the ticket: what it is, who has it, and how long it has been waiting. */
function CaseHeader({ data }: { data: CaseContext }) {
  const c = data.case
  const cl = data.classification
  const open = c.status === 'Open'
  const over = c.days_overdue > 0
  return (
    <section className="grid gap-4 rounded-md border border-line bg-card p-4 md:grid-cols-[1fr_auto]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="num text-sm text-gray-500">{c.complaint_id}</span>
          <Badge tone={statusTone(c.status)}>{c.status}</Badge>
          <PriorityBadge priority={cl?.priority ?? c.priority} />
          {cl && <LaneBadge lane={cl.lane} />}
          {c.transferred_between_systems && <Badge tone="amber">Transferred</Badge>}
        </div>
        <h1 className="mt-1.5 text-xl font-semibold tracking-tight text-ink">{cl?.subcategory ?? c.category}</h1>
        <p className="mt-1 text-sm text-gray-500">
          <Link to={`/accounts?account_id=${encodeURIComponent(c.account_id)}`} className="num text-brand hover:underline">
            {c.account_id}
          </Link>
          {' · '}
          {c.region} · {c.channel} · {c.source_system} · opened {shortDate(c.date_opened)}
        </p>
      </div>
      <div className="flex gap-6 border-line md:border-l md:pl-6">
        <div>
          <p className="text-[11px] tracking-wider text-gray-500 uppercase">Assigned to</p>
          <p className="mt-1 text-sm font-medium text-ink">{cl?.routed_team ?? 'Not routed yet'}</p>
        </div>
        <div>
          <p className="text-[11px] tracking-wider text-gray-500 uppercase">{open ? 'Days open' : 'Closed in'}</p>
          <p className={cn('num mt-0.5 text-2xl', c.breached_live ? 'text-red-700' : 'text-ink')}>
            {c.days_open}
            <span className="text-sm text-gray-400">/{c.sla_days}d</span>
          </p>
          <p className={cn('text-xs', over ? 'text-red-700' : 'text-gray-500')}>
            {over ? `${c.days_overdue} days over` : `${Math.abs(c.days_overdue)} days left`}
          </p>
        </div>
      </div>
    </section>
  )
}

const historyColumns: Column<AccountCase>[] = [
  {
    key: 'complaint_id',
    header: 'Complaint',
    cell: (r) => (
      <Link to={`/cases/${r.complaint_id}`} className="num text-brand hover:underline">
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
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]" aria-busy>
      <div className="flex flex-col gap-4">
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
    <div className="flex flex-col gap-4">
      <CaseHeader data={data} />
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-4">
          <AgentPanel data={data} />
          <Card>
            <CardTitle
              title="Account history"
              hint={`${num(data.account_complaints_total)} ${data.account_complaints_total === 1 ? 'complaint' : 'complaints'} on this account, oldest first`}
            />
            <DataTable columns={historyColumns} rows={data.account_history} rowKey={(r) => r.complaint_id} pageSize={5} />
          </Card>
        </div>

        <aside className="flex flex-col gap-4 lg:sticky lg:top-16">
          <Card>
            <CardTitle title="Details" />
            <dl>
              <Fact label="Category">{c.category}</Fact>
              <Fact label="Channel">{c.channel}</Fact>
              <Fact label="Source system">{c.source_system}</Fact>
              <Fact label="Opened">{shortDate(c.date_opened)}</Fact>
              <Fact label="SLA target">{c.sla_days} days</Fact>
              <Fact label="Transferred">{c.transferred_between_systems ? 'Yes' : 'No'}</Fact>
              {c.date_closed && <Fact label="Closed">{shortDate(c.date_closed)}</Fact>}
              {c.resolution_action && <Fact label="Resolution">{c.resolution_action}</Fact>}
              {c.bill_correction_value !== null && <Fact label="Bill correction">{num(c.bill_correction_value)}</Fact>}
            </dl>
          </Card>

          <Card>
            <CardTitle title="Triage" hint="What the classifier decided, and why" />
            {cl ? (
              <>
                <dl>
                  <Fact label="Group">
                    {cl.group_name}
                    <div className="text-xs text-gray-500">
                      {cl.group_source === 'laya' ? `Laya, ${pct(cl.group_confidence ?? 0)} sure` : `Recorded category (Laya ${pct(cl.group_confidence ?? 0)})`}
                    </div>
                  </Fact>
                  <Fact label="Subcategory">{cl.subcategory ?? '-'}</Fact>
                  <Fact label="Routed to">{cl.routed_team}</Fact>
                  <Fact label="Priority">
                    <PriorityBadge priority={cl.priority} />
                    {cl.priority !== cl.base_priority && <div className="text-xs text-gray-500">raised from {cl.base_priority}</div>}
                  </Fact>
                  <Fact label="Likely cause">{cl.likely_cause ? humanize(cl.likely_cause) : '-'}</Fact>
                </dl>
                {cl.flags.length > 0 && (
                  <ul className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
                    {cl.flags.map((flag) => (
                      <li key={flag.name} className="text-sm">
                        <Badge tone="amber">{humanize(flag.name)}</Badge>
                        {flag.reason && <p className="mt-1 text-xs text-gray-500">{flag.reason}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <div className="flex flex-col items-start gap-3">
                <p className="text-sm text-gray-500">Not classified yet.</p>
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
            <CardTitle title="Region meter picture" hint={`${c.region}, estimated-read rate by month`} />
            {data.region_meter.length === 0 ? (
              <p className="text-sm text-gray-500">No meter data for this region.</p>
            ) : (
              <>
                <div className="flex flex-col gap-2.5">
                  {data.region_meter.map((m) => (
                    <ShareBar key={m.month} label={monthName(m.month)} share={m.estimated_read_rate} />
                  ))}
                </div>
                <p className="mt-3 text-xs text-gray-500">
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
              <div className="flex flex-col gap-2.5">
                {mix.map((m) => (
                  <ShareBar key={m.resolution_action} label={m.resolution_action} share={m.share} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Nothing to compare with yet.</p>
            )}
            {data.category_profile?.avg_days != null && (
              <p className="mt-3 text-xs text-gray-500">
                Took {data.category_profile.avg_days} days on average; {pct(data.category_profile.transfer_rate ?? 0)} were transferred.
              </p>
            )}
          </Card>
        </aside>
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
      <nav className="flex items-center gap-1.5 text-sm text-gray-500">
        <Link to="/cases" className="inline-flex items-center gap-1 hover:text-brand">
          <ArrowLeft className="h-4 w-4" /> Cases
        </Link>
        <span className="text-gray-300">/</span>
        <span className="num text-ink">{id}</span>
      </nav>
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
