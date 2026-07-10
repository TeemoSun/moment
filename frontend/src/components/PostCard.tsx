import { Link } from 'react-router-dom'
import { useState } from 'react'
import { Heart, MessageCircle, Trash2, Lock } from 'lucide-react'
import { Card, Badge, Button } from 'liquidify-react'
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
      setLiked(false)
      setLikeCount((c) => c - 1)
    } else {
      await postApi.like(post.id)
      setLiked(true)
      setLikeCount((c) => c + 1)
    }
  }

  const handleDelete = async () => {
    if (!confirm('确定删除这条动态吗？')) return
    await postApi.delete(post.id)
    qc.invalidateQueries({ queryKey: ['feed'] })
    onDelete?.()
  }

  return (
    <Card variant="glass" padded className="mb-4">
      <div className="flex items-start gap-3">
        <Avatar user={post.user} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link to={`/u/${post.user.username}`} className="font-semibold text-ink-800 hover:text-accent transition-colors">
              {post.user.display_name || post.user.username}
            </Link>
            <span className="text-xs text-ink-400">{formatTime(post.created_at)}</span>
            {post.visibility === 'friends' && (
              <Badge tone="neutral" className="inline-flex items-center gap-1">
                <Lock size={10} /> 仅好友
              </Badge>
            )}
          </div>
          {post.content && (
            <p className="mt-2 text-ink-800 leading-relaxed whitespace-pre-wrap break-words">{post.content}</p>
          )}
          <MediaGrid media={post.media} />
          <div className="flex items-center gap-3 mt-3">
            <Button
              variant="plain"
              tone={liked ? 'destructive' : 'neutral'}
              size="compact"
              onClick={toggleLike}
              icon={<Heart size={16} fill={liked ? 'currentColor' : 'none'} />}
              aria-label="点赞"
            >
              {likeCount}
            </Button>
            <Link to={`/post/${post.id}`}>
              <Button variant="plain" tone="neutral" size="compact" icon={<MessageCircle size={16} />} aria-label="评论">
                {post.comment_count}
              </Button>
            </Link>
            {isOwner && onDelete && (
              <Button
                variant="plain"
                tone="neutral"
                size="compact"
                onClick={handleDelete}
                icon={<Trash2 size={16} />}
                aria-label="删除"
                className="ml-auto text-ink-400 hover:text-red-500"
              />
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}