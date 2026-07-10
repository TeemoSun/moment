import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { userApi, postApi } from '@/api'
import type { UserBrief } from '@/api/types'
import { PostCard } from '@/components/PostCard'
import { Avatar } from '@/components/Avatar'
import { useAuthStore } from '@/stores/auth'

export default function ProfilePage() {
  const { username } = useParams<{ username: string }>()
  const me = useAuthStore((s) => s.user)
  const isMe = me?.username === username

  const { data: profile } = useQuery({
    queryKey: ['user', username],
    queryFn: () => {
      if (isMe && me) return Promise.resolve(me)
      return userApi.getByUsername(username!)
    },
    enabled: !!username,
  })

  const { data: posts } = useQuery({
    queryKey: ['profile-posts', username, isMe],
    queryFn: () => {
      if (isMe) return postApi.myPosts(1, 50)
      return postApi.feed(1, 100)
    },
    enabled: !!username,
  })

  const visiblePosts = isMe
    ? posts?.items || []
    : (posts?.items || []).filter((p) => p.user.username === username)

  return (
    <div>
      {profile && (
        <div className="card mb-4">
          <div className="flex items-center gap-4">
            <Avatar user={profile as unknown as UserBrief} size={64} />
            <div>
              <h2 className="text-xl font-bold">{profile.display_name || profile.username}</h2>
              <p className="text-slate-400 text-sm">@{profile.username}</p>
              {profile.bio && <p className="text-slate-600 text-sm mt-1">{profile.bio}</p>}
            </div>
          </div>
        </div>
      )}
      <h3 className="text-slate-600 font-medium mb-2">动态</h3>
      {visiblePosts.map((p) => <PostCard key={p.id} post={p} />)}
      {visiblePosts.length === 0 && (
        <div className="text-center text-slate-400 py-8">
          {isMe ? '你还没有发布动态' : '该用户还没有动态，或者你无权查看'}
        </div>
      )}
    </div>
  )
}