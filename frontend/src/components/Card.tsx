import type { ReactNode } from 'react'
import { cn } from '../lib/cn'

export default function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-md border border-line bg-card p-4', className)}>{children}</section>
}

/** A small heading inside a card, with an optional hint on the right. */
export function CardTitle({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
      </div>
      {action}
    </div>
  )
}
