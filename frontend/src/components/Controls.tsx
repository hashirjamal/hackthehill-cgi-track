import { Search } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import Card from './Card'

// Each control works two ways: pass `value` and `onChange` to drive it (a filter that changes what the API returns),
// or leave them out and it keeps its own state (a page that is not connected to the API yet).

const field =
  'rounded-xl bg-gray-100 px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand/30'

export function FilterBar({ children, onClear }: { children: ReactNode; onClear?: () => void }) {
  return (
    <Card className="flex flex-wrap items-end gap-3 py-4">
      {children}
      {onClear && (
        <button type="button" onClick={onClear} className="rounded-xl px-3 py-2 text-sm font-medium text-brand hover:bg-brand-soft">
          Clear filters
        </button>
      )}
    </Card>
  )
}

/** A text box that reports what was typed once typing pauses, so each keystroke is not a request. */
export function SearchField({
  placeholder,
  className,
  value,
  onChange,
  delay = 350,
}: {
  placeholder: string
  className?: string
  value?: string
  onChange?: (value: string) => void
  delay?: number
}) {
  const [text, setText] = useState(value ?? '')

  // Follow the outside value when it changes from elsewhere, for example "Clear filters".
  useEffect(() => setText(value ?? ''), [value])

  useEffect(() => {
    if (!onChange || text === (value ?? '')) return
    const timer = setTimeout(() => onChange(text.trim()), delay)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  return (
    <label className={cn('flex flex-col gap-1 text-xs font-medium text-gray-500', className)}>
      <span>Search</span>
      <span className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder}
          className={cn(field, 'w-full min-w-52 pl-9')}
        />
      </span>
    </label>
  )
}

export type Option = string | { value: string; label: string }
const optionValue = (o: Option) => (typeof o === 'string' ? o : o.value)
const optionLabel = (o: Option) => (typeof o === 'string' ? o : o.label)

export function Select({
  label,
  options,
  value,
  onChange,
  allLabel = 'All',
}: {
  label: string
  options: Option[]
  value?: string
  onChange?: (value: string) => void
  allLabel?: string
}) {
  const controlled = onChange !== undefined
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-gray-500">
      <span>{label}</span>
      <select
        className={cn(field, 'min-w-36 pr-8')}
        {...(controlled ? { value: value ?? '', onChange: (e) => onChange(e.target.value) } : { defaultValue: '' })}
      >
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={optionValue(o)} value={optionValue(o)}>
            {optionLabel(o)}
          </option>
        ))}
      </select>
    </label>
  )
}

export function DateField({ label, value, onChange }: { label: string; value?: string; onChange?: (value: string) => void }) {
  const controlled = onChange !== undefined
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-gray-500">
      <span>{label}</span>
      <input
        type="date"
        className={field}
        {...(controlled ? { value: value ?? '', onChange: (e) => onChange(e.target.value) } : {})}
      />
    </label>
  )
}

/** A pill that switches on and off, for yes/no filters. */
export function ToggleChip({
  label,
  defaultOn = false,
  on,
  onChange,
}: {
  label: string
  defaultOn?: boolean
  on?: boolean
  onChange?: (on: boolean) => void
}) {
  const [own, setOwn] = useState(defaultOn)
  const active = onChange ? (on ?? false) : own
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={() => (onChange ? onChange(!active) : setOwn(!own))}
      className={cn(
        'rounded-full px-3.5 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand/30',
        active ? 'bg-brand text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
      )}
    >
      {label}
    </button>
  )
}

/** A row of pills where one is selected, for choosing how to group a report. */
export function SegmentedControl({
  label,
  options,
  defaultValue,
  value,
  onChange,
}: {
  label: string
  options: Option[]
  defaultValue?: string
  value?: string
  onChange?: (value: string) => void
}) {
  const [own, setOwn] = useState(defaultValue ?? optionValue(options[0]))
  const current = onChange ? (value ?? optionValue(options[0])) : own
  return (
    <div className="flex flex-col gap-1 text-xs font-medium text-gray-500">
      {label && <span>{label}</span>}
      <div className="flex flex-wrap gap-1 rounded-xl bg-gray-100 p-1">
        {options.map((o) => (
          <button
            key={optionValue(o)}
            type="button"
            aria-pressed={current === optionValue(o)}
            onClick={() => (onChange ? onChange(optionValue(o)) : setOwn(optionValue(o)))}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm transition-colors focus:outline-none',
              current === optionValue(o) ? 'bg-card font-medium text-brand shadow-sm' : 'text-gray-500 hover:text-gray-700',
            )}
          >
            {optionLabel(o)}
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
  disabled = false,
}: {
  children: ReactNode
  variant?: 'primary' | 'ghost'
  onClick?: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'rounded-xl px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:cursor-not-allowed disabled:opacity-50',
        variant === 'primary' ? 'bg-brand text-white hover:bg-brand-dark' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
      )}
    >
      {children}
    </button>
  )
}
