import type { ReactNode } from 'react'
import { cn } from '../lib/cn'
import type { Priority } from '../types'

const tones = {
  purple: 'bg-purple-100 text-purple-700',
  gray: 'bg-gray-100 text-gray-600',
  red: 'bg-red-100 text-red-700',
  amber: 'bg-amber-100 text-amber-700',
  green: 'bg-green-100 text-green-700',
}

export type Tone = keyof typeof tones

export default function Badge({ tone = 'gray', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap', tones[tone])}>
      {children}
    </span>
  )
}

const priorityTone: Record<Priority, Tone> = { P1: 'red', P2: 'amber', P3: 'gray' }

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge tone={priorityTone[priority]}>{priority}</Badge>
}

const laneTone: Record<string, Tone> = { emergency: 'red', review: 'amber', quick_lane: 'green', standard: 'gray' }

export function LaneBadge({ lane }: { lane: string | null }) {
  if (!lane) return <span className="text-gray-300">Not classified</span>
  return <Badge tone={laneTone[lane] ?? 'gray'}>{lane.replace('_', ' ')}</Badge>
}
