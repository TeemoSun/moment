import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { postApi, commentApi } from '@/api'
import { PostCard } from '@/components/PostCard'
import { CommentItem } from '@/components/CommentItem'
import { useState } from 'react'

export default function PostDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: post } = useQuery({ queryKey: ['post', id], queryFn: () => postApi.get(id!) })
  const { data: commentsData } = useQuery<
    import('@/api/types').Paginated<import('@/api/types').CommentTree>
  >({
    queryKey: ['comments', id],
    queryFn: () => commentApi.list(id!, 1, 100),
    enabled: !!id,
  })
  const [text, setText] = useState('')
  const qc = useQueryClient()

  const submitComment = async () => {
    if (!text.trim() || !id) return
    await commentApi.create(id, { content: text })
    setText('')
    qc.invalidateQueries({ queryKey: ['comments', id] })
    qc.invalidateQueries({ queryKey: ['post', id] })
    qc.invalidateQueries({ queryKey: ['feed'] })
  }

  return (
    <div>
      {post && <PostCard post={post} />}
      <div className="card mt-4">
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="写评论..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitComment()}
          />
          <button className="btn-primary" onClick={submitComment} disabled={!text.trim()}>
            发送
          </button>
        </div>
        <div className="mt-4">
          {commentsData?.items.map((tree) => (
            <div key={tree.root.id} className="border-b border-slate-50 last:border-0">
              <CommentItem comment={tree.root} postId={id!} />
              {tree.replies.map((reply) => (
                <CommentItem key={reply.id} comment={reply} postId={id!} />
              ))}
            </div>
          ))}
          {commentsData && commentsData.items.length === 0 && (
            <p className="text-center text-slate-400 py-4">还没有评论，来说点什么吧</p>
          )}
        </div>
      </div>
    </div>
  )
}