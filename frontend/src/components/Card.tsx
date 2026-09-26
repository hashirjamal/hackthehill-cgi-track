import type { ReactNode } from 'react'
import { cn } from '../lib/cn'

export default function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-2xl bg-card p-5', className)}>{children}</section>
}

/** A small heading inside a card, with an optional hint on the right. */
export function CardTitle({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div>
        <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-gray-400">{hint}</p>}
      </div>
      {action}
    </div>
  )
}
