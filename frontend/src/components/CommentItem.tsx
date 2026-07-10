import { Link } from 'react-router-dom'
import type { Comment } from '@/api/types'
import { Avatar } from './Avatar'
import { formatTime } from '@/utils'
import { commentApi } from '@/api'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export function CommentItem({
  comment,
  postId,
}: {
  comment: Comment
  postId: string
}) {
  const [liked, setLiked] = useState(comment.liked)
  const [likeCount, setLikeCount] = useState(comment.like_count)
  const [showReply, setShowReply] = useState(false)
  const [replyText, setReplyText] = useState('')
  const qc = useQueryClient()

  const toggleLike = async () => {
    if (liked) {
      await commentApi.unlike(comment.id)
      setLiked(false); setLikeCount((c) => c - 1)
    } else {
      await commentApi.like(comment.id)
      setLiked(true); setLikeCount((c) => c + 1)
    }
  }

  const submitReply = async () => {
    if (!replyText.trim()) return
    await commentApi.reply(comment.id, { content: replyText, reply_to_user_id: comment.user.id })
    setReplyText(''); setShowReply(false)
    qc.invalidateQueries({ queryKey: ['comments', postId] })
  }

  if (comment.deleted) {
    return <div className="text-slate-400 text-sm py-1">该评论已删除</div>
  }

  return (
    <div className="py-2" style={{ marginLeft: comment.depth > 0 ? Math.min(comment.depth, 5) * 20 : 0 }}>
      <div className="flex items-start gap-2">
        <Avatar user={comment.user} size={28} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link to={`/u/${comment.user.username}`} className="text-sm font-medium text-slate-700 hover:text-brand-600">
              {comment.user.display_name || comment.user.username}
            </Link>
            {comment.reply_to_user && comment.reply_to_user.id !== comment.user.id && (
              <span className="text-xs text-slate-400">
                回复 @{comment.reply_to_user.display_name || comment.reply_to_user.username}
              </span>
            )}
            <span className="text-xs text-slate-400">{formatTime(comment.created_at)}</span>
          </div>
          <p className="text-sm text-slate-600 mt-0.5 whitespace-pre-wrap break-words">{comment.content}</p>
          <div className="flex items-center gap-3 mt-1 text-xs">
            <button onClick={toggleLike} className={liked ? 'text-red-500' : 'text-slate-400'}>
              ♡ {likeCount}
            </button>
            <button onClick={() => setShowReply(!showReply)} className="text-slate-400 hover:text-brand-600">
              回复
            </button>
          </div>
          {showReply && (
            <div className="mt-2 flex gap-2">
              <input
                className="input text-sm"
                placeholder={`回复 @${comment.user.display_name || comment.user.username}`}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submitReply()}
              />
              <button className="btn-primary text-sm" onClick={submitReply}>发送</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}