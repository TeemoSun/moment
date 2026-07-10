import { useQuery, useQueryClient } from '@tanstack/react-query'
import { UserPlus, Check, X } from 'lucide-react'
import { Button, Card } from 'liquidify-react'
import { friendApi } from '@/api'
import type { FriendRequest, Friend } from '@/api/types'
import { Avatar } from '@/components/Avatar'
import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function FriendsPage() {
  const qc = useQueryClient()
  const [addUsername, setAddUsername] = useState('')
  const [msg, setMsg] = useState('')

  const { data: requests } = useQuery({ queryKey: ['friend-requests'], queryFn: friendApi.requests })
  const { data: friends } = useQuery({ queryKey: ['friends'], queryFn: friendApi.list })

  const sendRequest = async () => {
    if (!addUsername.trim()) return
    try {
      await friendApi.send(addUsername.trim())
      setMsg('好友请求已发送')
      setAddUsername('')
    } catch (err: any) {
      setMsg(err.response?.data?.detail || '发送失败')
    }
  }

  const accept = async (id: string) => {
    await friendApi.accept(id)
    qc.invalidateQueries({ queryKey: ['friend-requests'] })
    qc.invalidateQueries({ queryKey: ['friends'] })
  }

  const reject = async (id: string) => {
    await friendApi.reject(id)
    qc.invalidateQueries({ queryKey: ['friend-requests'] })
  }

  const remove = async (id: string) => {
    if (!confirm('确定删除该好友？')) return
    await friendApi.remove(id)
    qc.invalidateQueries({ queryKey: ['friends'] })
  }

  return (
    <div>
      <Card variant="glass" padded className="mb-4">
        <h2 className="font-semibold text-ink-800 mb-2 flex items-center gap-1.5">
          <UserPlus size={18} /> 添加好友
        </h2>
        <div className="flex gap-2">
          <input
            className="glass-input"
            placeholder="用户名"
            value={addUsername}
            onChange={(e) => setAddUsername(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendRequest()}
          />
          <Button variant="filled" tone="accent" onClick={sendRequest}>
            发送请求
          </Button>
        </div>
        {msg && <p className="text-sm text-ink-400 mt-2">{msg}</p>}
      </Card>

      {requests && requests.length > 0 && (
        <Card variant="glass" padded className="mb-4">
          <h2 className="font-semibold text-ink-800 mb-2">好友请求 ({requests.length})</h2>
          <div className="divide-y divide-ink-100/60">
            {requests.map((r: FriendRequest) => (
              <div key={r.id} className="flex items-center gap-3 py-2.5">
                <Avatar user={r.requester} size={36} />
                <Link to={`/u/${r.requester.username}`} className="font-medium text-ink-800 hover:text-accent transition-colors">
                  {r.requester.display_name || r.requester.username}
                </Link>
                <div className="ml-auto flex gap-2">
                  <Button variant="filled" tone="accent" size="compact" onClick={() => accept(r.id)} icon={<Check size={15} />}>
                    接受
                  </Button>
                  <Button variant="tinted" tone="neutral" size="compact" onClick={() => reject(r.id)} icon={<X size={15} />}>
                    拒绝
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card variant="glass" padded>
        <h2 className="font-semibold text-ink-800 mb-2">好友列表 ({friends?.length || 0})</h2>
        {friends && friends.length === 0 && <p className="text-ink-400 text-sm">还没有好友</p>}
        <div className="divide-y divide-ink-100/60">
          {friends?.map((f: Friend) => (
            <div key={f.id} className="flex items-center gap-3 py-2.5">
              <Avatar user={f.user} size={36} />
              <Link to={`/u/${f.user.username}`} className="font-medium text-ink-800 hover:text-accent transition-colors">
                {f.user.display_name || f.user.username}
              </Link>
              <Button variant="tinted" tone="neutral" size="compact" className="ml-auto" onClick={() => remove(f.id)}>
                删除
              </Button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}