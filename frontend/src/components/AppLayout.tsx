import { Outlet, useNavigate, Link, NavLink } from 'react-router-dom'
import { Home, Users, PlusCircle, Settings, LogOut, UserCircle } from 'lucide-react'
import { Button } from 'liquidify-react'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api'
import { Avatar } from './Avatar'

function NavItem({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ease-apple ${
          isActive
            ? 'bg-brand-500 text-white shadow-soft'
            : 'text-ink-600 hover:bg-ink-100/70 hover:text-ink-800'
        }`
      }
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </NavLink>
  )
}

export function AppLayout() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  const handleLogout = async () => {
    await authApi.logout().catch(() => {})
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen max-w-2xl mx-auto pb-24">
      <header className="sticky top-0 z-20 glass rounded-b-2xl">
        <div className="flex items-center justify-between px-4 py-2.5">
          <Link to="/" className="text-xl font-bold tracking-tight text-brand-500">
            Moment
          </Link>
          <nav className="flex items-center gap-1.5">
            <NavItem to="/" label="首页" icon={<Home size={18} />} />
            <NavItem to="/friends" label="好友" icon={<Users size={18} />} />
            <NavItem to="/compose" label="发布" icon={<PlusCircle size={18} />} />
            {user && (
              <div className="flex items-center gap-2 ml-1">
                <NavLink
                  to={`/u/${user.username}`}
                  className="flex items-center gap-1.5 text-sm text-ink-600 hover:text-ink-800 transition-colors"
                  title={user.display_name || user.username}
                >
                  <Avatar user={user as any} size={28} />
                </NavLink>
                <NavLink
                  to="/settings"
                  className={({ isActive }) =>
                    `p-2 rounded-full transition-colors ${
                      isActive ? 'bg-ink-100 text-ink-800' : 'text-ink-600 hover:bg-ink-100/70'
                    }`
                  }
                  title="设置"
                >
                  <Settings size={18} />
                </NavLink>
                <Button
                  variant="plain"
                  tone="neutral"
                  size="compact"
                  onClick={handleLogout}
                  aria-label="退出"
                  icon={<LogOut size={16} />}
                />
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className="px-4 py-5">
        <Outlet />
      </main>

      <footer className="fixed bottom-4 left-1/2 -translate-x-1/2 z-20 sm:hidden">
        <nav className="glass rounded-full px-3 py-2 flex items-center gap-1 shadow-glass">
          <NavLink to="/" end className="p-2 rounded-full text-ink-600 [&.active]:bg-brand-500 [&.active]:text-white">
            <Home size={20} />
          </NavLink>
          <NavLink to="/friends" className="p-2 rounded-full text-ink-600 [&.active]:bg-brand-500 [&.active]:text-white">
            <Users size={20} />
          </NavLink>
          <NavLink to="/compose" className="p-2 rounded-full text-ink-600 [&.active]:bg-brand-500 [&.active]:text-white">
            <PlusCircle size={20} />
          </NavLink>
          <NavLink to="/settings" className="p-2 rounded-full text-ink-600 [&.active]:bg-brand-500 [&.active]:text-white">
            <UserCircle size={20} />
          </NavLink>
        </nav>
      </footer>
    </div>
  )
}