import { X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '../lib/cn'
import { navGroups } from '../nav'

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-gray-900/30 md:hidden" onClick={onClose} aria-hidden />}
      <aside
        className={cn(
          'fixed top-3 bottom-3 left-3 z-30 flex w-60 flex-col rounded-2xl bg-card p-4 transition-transform md:sticky md:top-4 md:z-auto md:h-[calc(100vh-2rem)] md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-[120%]',
        )}
      >
        <div className="mb-6 flex items-center justify-between px-2 pt-1">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-600 text-sm font-bold text-white">N</div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-gray-800">Northwind</div>
              <div className="text-xs text-gray-400">Complaint triage</div>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close menu" className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 md:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-5 overflow-y-auto">
          {navGroups.map((group) => (
            <div key={group.title}>
              <div className="mb-1.5 px-3 text-xs font-medium tracking-wide text-gray-400 uppercase">{group.title}</div>
              <ul className="flex flex-col gap-0.5">
                {group.items.map(({ to, label, icon: Icon }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      onClick={onClose}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors',
                          isActive ? 'bg-purple-50 font-medium text-purple-600' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
                        )
                      }
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <p className="px-3 pt-4 text-xs text-gray-400">1,599 open complaints as of 30 Sep 2026</p>
      </aside>
    </>
  )
}
