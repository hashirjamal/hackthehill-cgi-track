import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'

export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="flex min-h-screen items-start">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header onMenu={() => setMenuOpen(true)} />
        <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-4 py-5 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
