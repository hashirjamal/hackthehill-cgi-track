import { CalendarDays, Menu, Search, User } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

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
    <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-line bg-card/95 px-4 py-2.5 backdrop-blur md:px-6">
      <button type="button" onClick={onMenu} aria-label="Open menu" className="rounded-xl p-2 text-gray-500 hover:bg-gray-100 md:hidden">
        <Menu className="h-5 w-5" />
      </button>

      <form onSubmit={open} className="relative max-w-md flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="Jump to case — e.g. NW-120404"
          className="w-full rounded-md border border-line bg-page py-1.5 pr-3 pl-9 font-mono text-sm text-gray-700 placeholder:text-gray-400 focus:ring-2 focus:ring-brand/30 focus:outline-none"
        />
      </form>

      <div className="ml-auto flex items-center gap-3">
        <span className="hidden items-center gap-1.5 text-xs text-gray-500 sm:flex">
          <CalendarDays className="h-4 w-4 text-gray-400" />
          As of 30 Sep 2026
        </span>
        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-page text-gray-500" aria-label="Account">
          <User className="h-4 w-4" />
        </div>
      </div>
    </header>
  )
}
