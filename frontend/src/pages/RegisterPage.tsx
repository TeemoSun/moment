import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Button, Card } from 'liquidify-react'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

export default function RegisterPage() {
  const [inviteCode, setInviteCode] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.register({ invite_code: inviteCode, username, email, password })
      setAuth(res.user, res.access_token)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card variant="glass" padded className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center text-ink-800 mb-1 tracking-tight">注册 Moment</h1>
        <p className="text-center text-sm text-ink-400 mb-6">创建你的账号</p>
        <form onSubmit={submit} className="space-y-3">
          <input className="glass-input" placeholder="邀请码" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} />
          <input
            className="glass-input"
            placeholder="用户名（3-32位）"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input className="glass-input" type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input
            className="glass-input"
            type="password"
            placeholder="密码（至少8位）"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <Button type="submit" variant="filled" tone="accent" className="w-full" disabled={loading} loading={loading}>
            {loading ? '注册中...' : '注册'}
          </Button>
        </form>
        <p className="text-center text-sm text-ink-400 mt-4">
          已有账号？<Link to="/login" className="text-accent font-medium">登录</Link>
        </p>
      </Card>
    </div>
  )
}