import { Outlet, useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api'

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
    <div className="min-h-screen max-w-2xl mx-auto pb-20">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-slate-100">
        <div className="flex items-center justify-between px-4 py-3">
          <Link to="/" className="text-xl font-bold text-brand-600">Moment</Link>
          <nav className="flex items-center gap-3">
            <Link to="/" className="text-slate-600 hover:text-brand-600">首页</Link>
            <Link to="/friends" className="text-slate-600 hover:text-brand-600">好友</Link>
            <Link to="/compose" className="text-slate-600 hover:text-brand-600">发布</Link>
            {user && (
              <div className="flex items-center gap-2">
                <Link to={`/u/${user.username}`} className="text-slate-600 hover:text-brand-600">
                  {user.display_name || user.username}
                </Link>
                <Link to="/settings" className="text-slate-600 hover:text-brand-600">设置</Link>
                <button onClick={handleLogout} className="btn-ghost text-sm">退出</button>
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className="px-4 py-4">
        <Outlet />
      </main>
    </div>
  )
}