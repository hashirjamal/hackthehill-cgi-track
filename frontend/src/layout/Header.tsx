import { CalendarDays, Menu, Search, User } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Badge from '../components/Badge'

export default function Header({ onMenu }: { onMenu: () => void }) {
  const [id, setId] = useState('')
  const navigate = useNavigate()

  const open = (e: FormEvent) => {
    e.preventDefault()
    const value = id.trim().toUpperCase()
    if (value) navigate(`/cases/${value}`)
    setId('')
  }

  return (
    <header className="flex items-center gap-3 rounded-2xl bg-card px-4 py-3">
      <button type="button" onClick={onMenu} aria-label="Open menu" className="rounded-xl p-2 text-gray-500 hover:bg-gray-100 md:hidden">
        <Menu className="h-5 w-5" />
      </button>

      <form onSubmit={open} className="relative max-w-md flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="Open a complaint, e.g. NW-120404"
          className="w-full rounded-xl bg-gray-100 py-2 pr-3 pl-9 text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-brand/30 focus:outline-none"
        />
      </form>

      <div className="ml-auto flex items-center gap-3">
        <Badge tone="amber" dot={false}>Sample data</Badge>
        <span className="hidden items-center gap-1.5 text-xs text-gray-500 sm:flex">
          <CalendarDays className="h-4 w-4 text-brand" />
          As of 30 Sep 2026
        </span>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft text-brand" aria-label="Account">
          <User className="h-4 w-4" />
        </div>
      </div>
    </header>
  )
}
