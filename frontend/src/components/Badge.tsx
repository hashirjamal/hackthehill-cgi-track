import type { ReactNode } from 'react'
import { cn } from '../lib/cn'
import type { Priority } from '../types'

// Soft tinted chip with a small dot: readable at a glance, no borders.
const tones = {
  brand: { chip: 'bg-brand-soft text-brand', dot: 'bg-brand' },
  gray: { chip: 'bg-gray-100 text-gray-700', dot: 'bg-gray-400' },
  red: { chip: 'bg-red-50 text-red-700', dot: 'bg-red-500' },
  amber: { chip: 'bg-amber-50 text-amber-800', dot: 'bg-amber-500' },
  green: { chip: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500' },
}

export type Tone = keyof typeof tones

export default function Badge({
  tone = 'gray',
  dot = true,
  children,
}: {
  tone?: Tone
  /** Show the leading dot. Turn it off for labels that are not a state. */
  dot?: boolean
  children: ReactNode
}) {
  const t = tones[tone]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full py-1 text-xs leading-none font-semibold whitespace-nowrap',
        dot ? 'pr-3 pl-2.5' : 'px-3',
        t.chip,
      )}
    >
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full', t.dot)} />}
      {children}
    </span>
  )
}

const priorityTone: Record<Priority, Tone> = { P1: 'red', P2: 'amber', P3: 'gray' }

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge tone={priorityTone[priority]}>{priority}</Badge>
}

const lanes: Record<string, { label: string; tone: Tone }> = {
  emergency: { label: 'Emergency', tone: 'red' },
  review: { label: 'Review', tone: 'amber' },
  quick_lane: { label: 'Quick lane', tone: 'green' },
  standard: { label: 'Standard', tone: 'gray' },
}

export function LaneBadge({ lane }: { lane: string | null }) {
  if (!lane) return <span className="text-gray-400">Not classified</span>
  const l = lanes[lane] ?? { label: lane, tone: 'gray' as Tone }
  return <Badge tone={l.tone}>{l.label}</Badge>
}
