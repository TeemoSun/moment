import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const res = await authApi.login({ username, password })
      setAuth(res.user, res.access_token)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || '登录失败')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="card w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center text-brand-600 mb-6">登录 Moment</h1>
        <form onSubmit={submit} className="space-y-3">
          <input className="input" placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input className="input" type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        <p className="text-center text-sm text-slate-400 mt-4">
          没有账号？<Link to="/register" className="text-brand-600">注册</Link>
        </p>
      </div>
    </div>
  )
}