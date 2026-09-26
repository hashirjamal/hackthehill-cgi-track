import { useState } from 'react'
import Card, { CardTitle } from '../components/Card'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { money } from '../lib/format'

// A preview calculation from the numbers in the data pack. The real simulator will use the API
// (baseline from the database, costs from the unit cost table).
const BASE = {
  opened: 13709, // complaints in the last 12 months
  transferShare: 0.35,
  daysNow: 38.2,
  daysTransferred: 38.2,
  daysNotTransferred: 23.0,
  standardCost: 68,
  transferredCost: 121,
  callCost: 7.4,
  staffAnnual: 46000,
  staffHire: 11500,
  penaltyQuarter: 2_400_000,
  fastLanePrecision: 0.54,
  hiresNeeded: 2.9,
}

const avgDays = (t: number) => t * BASE.daysTransferred + (1 - t) * BASE.daysNotTransferred

function simulate(transferCut: number, fastLane: number, fastLaneDays: number) {
  const t = BASE.transferShare * (1 - transferCut)
  const correct = fastLane * BASE.fastLanePrecision
  const scale = BASE.daysNow / avgDays(BASE.transferShare)
  const days = (1 - correct) * scale * avgDays(t) + correct * fastLaneDays

  const perComplaint = BASE.transferShare * BASE.transferredCost + (1 - BASE.transferShare) * BASE.standardCost
  const transferSaving = BASE.opened * (BASE.transferShare - t) * (BASE.transferredCost - BASE.standardCost)
  const fastSaving =
    BASE.opened * correct * (perComplaint - BASE.callCost) - BASE.opened * fastLane * (1 - BASE.fastLanePrecision) * BASE.callCost
  const saving = transferSaving + fastSaving

  return {
    days,
    score: Math.min(5, Math.max(1, 5.578 - 0.0785 * days)),
    baseCost: BASE.opened * perComplaint,
    transferSaving,
    fastSaving,
    saving,
    staffFreed: saving / BASE.staffAnnual,
    hiringCost: BASE.hiresNeeded * (BASE.staffAnnual + BASE.staffHire),
  }
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  format: (v: number) => string
  onChange: (v: number) => void
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="flex items-baseline justify-between text-sm">
        <span className="text-gray-700">{label}</span>
        <span className="font-semibold text-brand tabular-nums">{format(value)}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-brand"
      />
    </label>
  )
}

export default function Simulator() {
  const [transferCut, setTransferCut] = useState(0.4)
  const [fastLane, setFastLane] = useState(0.1)
  const [fastLaneDays, setFastLaneDays] = useState(2)
  const [quarters, setQuarters] = useState(0)
  const r = simulate(transferCut, fastLane, fastLaneDays)

  return (
    <>
      <PageHeader
        title="Simulator"
        description="What the system is worth: move the levers we control and see the effect on resolution time, cost and the regulator score."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="flex flex-col gap-6">
          <CardTitle title="Levers" hint="Conservative defaults" />
          <Slider label="Transfers removed" value={transferCut} min={0} max={1} step={0.05} format={(v) => `${Math.round(v * 100)}%`} onChange={setTransferCut} />
          <Slider label="Cases sent to the quick lane" value={fastLane} min={0} max={0.3} step={0.01} format={(v) => `${Math.round(v * 100)}%`} onChange={setFastLane} />
          <Slider label="Quick-lane close time" value={fastLaneDays} min={1} max={10} step={1} format={(v) => `${v} days`} onChange={setFastLaneDays} />
          <Slider label="Quarters out of regulator breach" value={quarters} min={0} max={4} step={1} format={(v) => `${v}`} onChange={setQuarters} />
          <p className="text-xs text-gray-400">
            Only about half of the cases sent to the quick lane are truly information-only, so the saving counts 54% of them.
          </p>
        </Card>

        <div className="flex flex-col gap-4 lg:col-span-2">
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
            <StatCard label="Average days to close" value={r.days.toFixed(1)} hint={`Now ${BASE.daysNow}. Target about 20`} />
            <StatCard label="Estimated regulator score" value={r.score.toFixed(2)} hint="Now 2.58. An estimate, from a correlation" />
            <StatCard label="Handling saving a year" value={money(r.saving)} hint={`On ${money(r.baseCost)} today`} />
            <StatCard label="Staff time freed" value={r.staffFreed.toFixed(1)} hint="Full-time staff equivalents" />
            <StatCard label="Hiring instead" value={money(r.hiringCost)} hint="About 3 extra staff, year one" />
            <StatCard label="Penalty avoided" value={money(quarters * BASE.penaltyQuarter)} hint="2.4M for each quarter out of breach" />
          </div>

          <Card>
            <CardTitle title="Where the saving comes from" hint="Handling cost per year, before any running cost" />
            <dl className="grid gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-gray-400">Fewer transfers</dt>
                <dd className="mt-0.5 text-lg font-semibold text-gray-800 tabular-nums">{money(r.transferSaving)}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Quick lane</dt>
                <dd className="mt-0.5 text-lg font-semibold text-gray-800 tabular-nums">{money(r.fastSaving)}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Most the system can cost a year</dt>
                <dd className="mt-0.5 text-lg font-semibold text-brand tabular-nums">{money(r.saving)}</dd>
              </div>
            </dl>
            <p className="mt-4 text-xs text-gray-400">
              On handling cost alone the system is worth about as much as hiring three people. The larger prize is avoiding the
              regulator penalty and getting resolution time back to about 20 days.
            </p>
          </Card>
        </div>
      </div>
    </>
  )
}
