import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/companies', label: 'Companies' },
  { to: '/persons', label: 'Persons' },
  { to: '/graph', label: 'Graph' },
  { to: '/warm-intro', label: 'Warm Intro' },
  { to: '/warmup', label: 'Warmup' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-slate-900 border-r border-slate-800 p-4">
        <h1 className="text-lg font-bold text-white mb-6">Outreach AI Cortex</h1>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm transition ${
                  isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
