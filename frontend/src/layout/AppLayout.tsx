import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'

export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="flex min-h-screen items-start gap-4 p-3 md:p-4">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <Header onMenu={() => setMenuOpen(true)} />
        <main className="flex flex-col gap-4 pb-4">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
