import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Send } from 'lucide-react'
import { Button, Card } from 'liquidify-react'
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
      <Card variant="glass" padded className="mt-4">
        <div className="flex gap-2">
          <input
            className="glass-input"
            placeholder="写评论..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitComment()}
          />
          <Button variant="filled" tone="accent" onClick={submitComment} disabled={!text.trim()} icon={<Send size={16} />} aria-label="发送">
            发送
          </Button>
        </div>
        <div className="mt-4 divide-y divide-ink-100/60">
          {commentsData?.items.map((tree) => (
            <div key={tree.root.id}>
              <CommentItem comment={tree.root} postId={id!} />
              {tree.replies.map((reply) => (
                <CommentItem key={reply.id} comment={reply} postId={id!} />
              ))}
            </div>
          ))}
          {commentsData && commentsData.items.length === 0 && (
            <p className="text-center text-ink-400 py-4">还没有评论，来说点什么吧</p>
          )}
        </div>
      </Card>
    </div>
  )
}