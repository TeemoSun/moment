import { Link } from 'react-router-dom'
import { useState } from 'react'
import type { Post } from '@/api/types'
import { postApi } from '@/api'
import { useQueryClient } from '@tanstack/react-query'
import { Avatar } from './Avatar'
import { MediaGrid } from './MediaGrid'
import { formatTime } from '@/utils'
import { useAuthStore } from '@/stores/auth'

export function PostCard({ post, onDelete }: { post: Post; onDelete?: () => void }) {
  const user = useAuthStore((s) => s.user)
  const [liked, setLiked] = useState(post.liked)
  const [likeCount, setLikeCount] = useState(post.like_count)
  const qc = useQueryClient()
  const isOwner = user?.id === post.user.id

  const toggleLike = async () => {
    if (liked) {
      await postApi.unlike(post.id)
      setLiked(false); setLikeCount((c) => c - 1)
    } else {
      await postApi.like(post.id)
      setLiked(true); setLikeCount((c) => c + 1)
    }
  }

  const handleDelete = async () => {
    if (!confirm('确定删除这条动态吗？')) return
    await postApi.delete(post.id)
    qc.invalidateQueries({ queryKey: ['feed'] })
    onDelete?.()
  }

  return (
    <div className="card mb-4">
      <div className="flex items-start gap-3">
        <Avatar user={post.user} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Link to={`/u/${post.user.username}`} className="font-medium text-slate-800 hover:text-brand-600">
              {post.user.display_name || post.user.username}
            </Link>
            <span className="text-xs text-slate-400">{formatTime(post.created_at)}</span>
            {post.visibility === 'friends' && <span className="text-xs text-amber-600">仅好友可见</span>}
          </div>
          {post.content && (
            <p className="mt-2 text-slate-700 whitespace-pre-wrap break-words">{post.content}</p>
          )}
          <MediaGrid media={post.media} />
          <div className="flex items-center gap-4 mt-3 text-sm">
            <button onClick={toggleLike} className={`flex items-center gap-1 ${liked ? 'text-red-500' : 'text-slate-500'}`}>
              {liked ? '❤' : '♡'} {likeCount}
            </button>
            <Link to={`/post/${post.id}`} className="text-slate-500 hover:text-brand-600">
              💬 {post.comment_count}
            </Link>
            {isOwner && onDelete && (
              <button onClick={handleDelete} className="text-slate-400 hover:text-red-500 ml-auto">删除</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}