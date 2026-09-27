import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useIntake, type IntakeComplaint, type IntakeResult } from '../api/reports'
import Badge, { LaneBadge, PriorityBadge } from '../components/Badge'
import Card, { CardTitle } from '../components/Card'
import { Button, Select } from '../components/Controls'
import PageHeader from '../components/PageHeader'
import { CHANNELS, REGIONS } from '../constants'
import { humanize } from '../lib/format'

// The four systems complaints come in through. Everything else in the estate is upstream or downstream.
const INTAKE_SYSTEMS = [
  { value: 'SYS-05', label: 'CallCentre One (phone)' },
  { value: 'SYS-03', label: 'Northwind Connect (web / app)' },
  { value: 'SYS-01', label: 'Aurora Billing' },
  { value: 'SYS-04', label: 'CaseTrack' },
]

const EMPTY: IntakeComplaint = { account_id: '', text: '', channel: 'Phone', region: '', source_system: 'SYS-05' }

const field =
  'rounded-xl bg-gray-100 px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand/30'

function Result({ result }: { result: IntakeResult }) {
  const c = result.classification
  return (
    <Card>
      <CardTitle title={`Logged as ${result.complaint_id}`} hint="Classified by Laya and on the worklist now." />
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <dt className="text-xs font-medium text-gray-500">Group</dt>
          <dd className="mt-1 text-sm text-gray-800">{c.emergency ? 'Emergency' : (c.group?.name ?? 'Needs review')}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500">Category</dt>
          <dd className="mt-1 text-sm text-gray-800">{result.category}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500">Urgency</dt>
          <dd className="mt-1">
            <PriorityBadge priority={c.priority.level} /> <span className="text-xs text-gray-500">{c.priority.target_days} days</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500">Routed to</dt>
          <dd className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-800">
            {c.routing.team} <LaneBadge lane={c.routing.lane} />
          </dd>
        </div>
      </dl>
      {c.flags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {c.flags.map((f) => (
            <Badge key={f.name} tone="amber">
              {humanize(f.name)}
            </Badge>
          ))}
        </div>
      )}
      <Link to={`/cases/${result.complaint_id}`} className="mt-5 inline-block text-sm font-medium text-brand hover:underline">
        Open the case →
      </Link>
    </Card>
  )
}

/** The intake template the four intake systems fill in. Laya reads the text, so the text matters most. */
export default function Intake() {
  const [form, setForm] = useState<IntakeComplaint>(EMPTY)
  const intake = useIntake()
  const set = (key: keyof IntakeComplaint) => (value: string) => setForm((f) => ({ ...f, [key]: value }))
  const ready = form.account_id.trim() !== '' && form.text.trim() !== '' && form.region !== ''

  const submit = () =>
    intake.mutate(form, {
      onSuccess: () => setForm(EMPTY),
    })

  return (
    <div className="space-y-6">
      <PageHeader
        title="New complaint"
        description="Log a complaint as it comes in. Laya reads what the customer said and decides the group and how urgent it is - no category or priority to pick."
      />

      <Card>
        <CardTitle title="Intake template" hint="Write what the customer said as fully as you can. Laya works from the text." />
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs font-medium text-gray-500">
            <span>Account ID</span>
            <input className={field} value={form.account_id} onChange={(e) => set('account_id')(e.target.value)} placeholder="e.g. ACC-104233" />
          </label>
          <Select label="Region" options={REGIONS} value={form.region} onChange={set('region')} allLabel="Choose a region" />
          <Select label="Received through" options={INTAKE_SYSTEMS} value={form.source_system} onChange={set('source_system')} allLabel="Choose a system" />
          <Select label="Channel" options={CHANNELS} value={form.channel} onChange={set('channel')} allLabel="Choose a channel" />
          <label className="flex flex-col gap-1 text-xs font-medium text-gray-500 sm:col-span-2">
            <span>What the customer said</span>
            <textarea
              className={`${field} min-h-36`}
              value={form.text}
              onChange={(e) => set('text')(e.target.value)}
              placeholder="e.g. My bill is twice what it usually is. I think it's an estimate - nobody has read the meter in months. I can't afford to pay it."
            />
          </label>
        </div>
        <div className="mt-5 flex items-center gap-3">
          <Button onClick={submit} disabled={!ready || intake.isPending}>
            {intake.isPending ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Classifying…
              </span>
            ) : (
              'Log and classify'
            )}
          </Button>
          {!ready && <span className="text-sm text-gray-500">Account, region and the customer's words are needed.</span>}
        </div>
      </Card>

      {intake.data && <Result result={intake.data} />}
    </div>
  )
}
