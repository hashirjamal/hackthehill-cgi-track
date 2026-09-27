import { ChevronRight, Database } from 'lucide-react'
import { cn } from '../lib/cn'
import type { SystemCall } from '../types'

// Each system keeps the colours of its own console, so staff recognise it at a glance.
const SYSTEM_STYLE: Record<SystemCall['system'], { chip: string; label: string; era: string }> = {
  aurora: { chip: 'bg-black text-[#33ff33] font-mono', label: 'AURORA', era: 'Mainframe billing, 1998' },
  helix: { chip: 'bg-[#0a246a] text-white', label: 'Helix CIS', era: 'Customer records, 2004' },
  casetrack: { chip: 'bg-[#5b2c6f] text-white', label: 'CaseTrack', era: 'Case management, 2011' },
  callcentre: { chip: 'bg-teal-700 text-white', label: 'CallCentre One', era: 'Telephony + CRM, 2015' },
  connect: { chip: 'bg-indigo-600 text-white', label: 'Connect', era: 'Customer portal, 2019' },
}

/** Which Northwind systems the agent looked at, what it was told, and the raw record behind it. */
export default function SystemsChecked({ calls }: { calls: SystemCall[] }) {
  if (calls.length === 0) return null
  const distinct = new Set(calls.map((c) => c.system)).size
  return (
    <div className="mt-4">
      <p className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
        <Database className="h-3.5 w-3.5" />
        Systems checked: {distinct} {distinct === 1 ? 'system' : 'systems'}, {calls.length} {calls.length === 1 ? 'lookup' : 'lookups'}
      </p>
      <ul className="mt-2 flex flex-col gap-1.5">
        {calls.map((c, i) => {
          const s = SYSTEM_STYLE[c.system]
          return (
            <li key={i}>
              <details className="group rounded-xl bg-gray-100">
                <summary className="flex cursor-pointer list-none items-start gap-2 p-2.5 text-sm">
                  <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-gray-400 transition-transform group-open:rotate-90" />
                  <span className={cn('shrink-0 rounded-md px-2 py-0.5 text-xs', s.chip)} title={s.era}>
                    {s.label}
                  </span>
                  <span className={cn('min-w-0 text-gray-700', !c.raw && 'text-amber-700')}>
                    {firstLine(c.summary) ?? 'Looked up'}
                  </span>
                </summary>
                <div className="grid gap-3 border-t border-gray-200 p-3 lg:grid-cols-2">
                  <div className="min-w-0">
                    <p className="mb-1 text-xs font-medium text-gray-500">What the system returned</p>
                    <p className="mb-1 truncate font-mono text-[11px] text-gray-400">{c.request}</p>
                    <pre className="max-h-72 overflow-auto rounded-lg bg-gray-900 p-2.5 text-[11px] leading-snug text-gray-100">
                      {c.raw ?? '(no response)'}
                    </pre>
                  </div>
                  <div className="min-w-0">
                    <p className="mb-1 text-xs font-medium text-gray-500">What the AI took from it</p>
                    <p className="text-sm whitespace-pre-wrap text-gray-700">{c.summary ?? '-'}</p>
                  </div>
                </div>
              </details>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

const firstLine = (text: string | null) => (text ? text.split('\n')[0] : null)
