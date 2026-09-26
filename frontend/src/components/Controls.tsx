import { Search } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import Card from './Card'

const field =
  'rounded-xl bg-gray-100 px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-300'

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <Card className="flex flex-wrap items-end gap-3 py-4">{children}</Card>
  )
}

export function SearchField({ placeholder, className }: { placeholder: string; className?: string }) {
  return (
    <label className={cn('flex flex-col gap-1 text-xs text-gray-400', className)}>
      <span>Search</span>
      <span className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input type="search" placeholder={placeholder} className={cn(field, 'w-full min-w-52 pl-9')} />
      </span>
    </label>
  )
}

export function Select({ label, options }: { label: string; options: string[] }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-gray-400">
      <span>{label}</span>
      <select className={cn(field, 'min-w-36 pr-8')} defaultValue="">
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  )
}

export function DateField({ label }: { label: string }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-gray-400">
      <span>{label}</span>
      <input type="date" className={field} />
    </label>
  )
}

/** A pill that switches on and off, for yes/no filters. */
export function ToggleChip({ label, defaultOn = false }: { label: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn)
  return (
    <button
      type="button"
      onClick={() => setOn(!on)}
      className={cn(
        'rounded-full px-3.5 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-purple-300',
        on ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
      )}
    >
      {label}
    </button>
  )
}

/** A row of pills where one is selected, for choosing how to group a report. */
export function SegmentedControl({ label, options, defaultValue }: { label: string; options: string[]; defaultValue?: string }) {
  const [value, setValue] = useState(defaultValue ?? options[0])
  return (
    <div className="flex flex-col gap-1 text-xs text-gray-400">
      <span>{label}</span>
      <div className="flex flex-wrap gap-1 rounded-xl bg-gray-100 p-1">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            onClick={() => setValue(o)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm transition-colors focus:outline-none',
              value === o ? 'bg-card font-medium text-purple-600 shadow-sm' : 'text-gray-500 hover:text-gray-700',
            )}
          >
            {o}
          </button>
        ))}
      </div>
    </div>
  )
}

export function Button({
  children,
  variant = 'primary',
  onClick,
}: {
  children: ReactNode
  variant?: 'primary' | 'ghost'
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-xl px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-purple-300',
        variant === 'primary' ? 'bg-purple-600 text-white hover:bg-purple-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
      )}
    >
      {children}
    </button>
  )
}
