import { X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '../lib/cn'
import { useWorklistTotal } from '../api/reports'
import { num } from '../lib/format'
import { navGroups } from '../nav'

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  // The same query as the Worklist's first stat card, so it is asked for once.
  const openCount = useWorklistTotal({}, 'the summary numbers')
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-gray-900/30 md:hidden" onClick={onClose} aria-hidden />}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 flex w-56 flex-col border-r border-line bg-card px-3 py-4 transition-transform md:sticky md:top-0 md:z-auto md:h-screen md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-[120%]',
        )}
      >
        <div className="mb-5 flex items-center justify-between border-b border-line px-2 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand font-mono text-sm font-medium text-white">T</div>
            <div className="leading-tight">
              <div className="text-[15px] font-semibold tracking-tight text-ink">Trev</div>
              <div className="text-xs text-gray-500">Complaints desk</div>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close menu" className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 md:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-5 overflow-y-auto">
          {navGroups.map((group) => (
            <div key={group.title}>
              <div className="mb-1 px-2 text-[11px] font-medium tracking-wider text-gray-400 uppercase">{group.title}</div>
              <ul className="flex flex-col gap-0.5">
                {group.items.map(({ to, label, icon: Icon }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      onClick={onClose}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-2.5 rounded-md border-l-2 px-2 py-1.5 text-sm transition-colors',
                          isActive ? 'border-brand bg-brand-soft font-medium text-brand-dark' : 'border-transparent text-gray-600 hover:bg-page hover:text-ink',
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

        <p className="border-t border-line px-2 pt-3 text-xs text-gray-500">
          {openCount.isSuccess ? `${num(openCount.data)} open complaints as of 30 Sep 2026` : 'Data as of 30 Sep 2026'}
        </p>
      </aside>
    </>
  )
}
