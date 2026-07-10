import { useQuery, useQueryClient } from '@tanstack/react-query'
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
      <div className="card mb-4">
        <h2 className="font-medium mb-2">添加好友</h2>
        <div className="flex gap-2">
          <input className="input" placeholder="用户名" value={addUsername} onChange={(e) => setAddUsername(e.target.value)} />
          <button className="btn-primary" onClick={sendRequest}>发送请求</button>
        </div>
        {msg && <p className="text-sm text-slate-500 mt-2">{msg}</p>}
      </div>

      {requests && requests.length > 0 && (
        <div className="card mb-4">
          <h2 className="font-medium mb-2">好友请求 ({requests.length})</h2>
          {requests.map((r: FriendRequest) => (
            <div key={r.id} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
              <Avatar user={r.requester} size={36} />
              <Link to={`/u/${r.requester.username}`} className="font-medium">{r.requester.display_name || r.requester.username}</Link>
              <div className="ml-auto flex gap-2">
                <button className="btn-primary text-sm" onClick={() => accept(r.id)}>接受</button>
                <button className="btn-ghost text-sm" onClick={() => reject(r.id)}>拒绝</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2 className="font-medium mb-2">好友列表 ({friends?.length || 0})</h2>
        {friends && friends.length === 0 && <p className="text-slate-400 text-sm">还没有好友</p>}
        {friends?.map((f: Friend) => (
          <div key={f.id} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
            <Avatar user={f.user} size={36} />
            <Link to={`/u/${f.user.username}`} className="font-medium">{f.user.display_name || f.user.username}</Link>
            <button className="btn-ghost text-sm ml-auto" onClick={() => remove(f.id)}>删除</button>
          </div>
        ))}
      </div>
    </div>
  )
}