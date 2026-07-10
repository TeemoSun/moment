import { Link } from 'react-router-dom'
import { useState } from 'react'
import { Heart, CornerUpRight, Send } from 'lucide-react'
import { Button } from 'liquidify-react'
import type { Comment } from '@/api/types'
import { Avatar } from './Avatar'
import { formatTime } from '@/utils'
import { commentApi } from '@/api'
import { useQueryClient } from '@tanstack/react-query'

export function CommentItem({ comment, postId }: { comment: Comment; postId: string }) {
  const [liked, setLiked] = useState(comment.liked)
  const [likeCount, setLikeCount] = useState(comment.like_count)
  const [showReply, setShowReply] = useState(false)
  const [replyText, setReplyText] = useState('')
  const qc = useQueryClient()

  const toggleLike = async () => {
    if (liked) {
      await commentApi.unlike(comment.id)
      setLiked(false)
      setLikeCount((c) => c - 1)
    } else {
      await commentApi.like(comment.id)
      setLiked(true)
      setLikeCount((c) => c + 1)
    }
  }

  const submitReply = async () => {
    if (!replyText.trim()) return
    await commentApi.reply(comment.id, { content: replyText, reply_to_user_id: comment.user.id })
    setReplyText('')
    setShowReply(false)
    qc.invalidateQueries({ queryKey: ['comments', postId] })
  }

  if (comment.deleted) {
    return <div className="text-ink-400 text-sm py-1">该评论已删除</div>
  }

  return (
    <div className="py-2" style={{ marginLeft: comment.depth > 0 ? Math.min(comment.depth, 5) * 20 : 0 }}>
      <div className="flex items-start gap-2">
        <Avatar user={comment.user} size={28} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link to={`/u/${comment.user.username}`} className="text-sm font-medium text-ink-800 hover:text-accent transition-colors">
              {comment.user.display_name || comment.user.username}
            </Link>
            {comment.reply_to_user && comment.reply_to_user.id !== comment.user.id && (
              <span className="text-xs text-ink-400 inline-flex items-center gap-0.5">
                <CornerUpRight size={11} /> {comment.reply_to_user.display_name || comment.reply_to_user.username}
              </span>
            )}
            <span className="text-xs text-ink-400">{formatTime(comment.created_at)}</span>
          </div>
          <p className="text-sm text-ink-800 mt-0.5 leading-relaxed whitespace-pre-wrap break-words">{comment.content}</p>
          <div className="flex items-center gap-2 mt-1">
            <Button
              variant="plain"
              tone={liked ? 'destructive' : 'neutral'}
              size="compact"
              onClick={toggleLike}
              icon={<Heart size={13} fill={liked ? 'currentColor' : 'none'} />}
              aria-label="点赞"
              className="!text-xs"
            >
              {likeCount}
            </Button>
            <Button
              variant="plain"
              tone="neutral"
              size="compact"
              onClick={() => setShowReply(!showReply)}
              className="!text-xs"
            >
              回复
            </Button>
          </div>
          {showReply && (
            <div className="mt-2 flex gap-2">
              <input
                className="glass-input text-sm"
                placeholder={`回复 @${comment.user.display_name || comment.user.username}`}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submitReply()}
              />
              <Button variant="filled" tone="accent" size="compact" onClick={submitReply} icon={<Send size={15} />} aria-label="发送">
                发送
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}