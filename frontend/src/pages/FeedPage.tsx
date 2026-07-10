import { useInfiniteQuery } from '@tanstack/react-query'
import { postApi } from '@/api'
import { PostCard } from '@/components/PostCard'
import { Fragment } from 'react'

export default function FeedPage() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } = useInfiniteQuery({
    queryKey: ['feed'],
    queryFn: ({ pageParam = 1 }) => postApi.feed(pageParam, 20),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.has_more ? last.page + 1 : undefined),
  })

  if (isLoading) return <div className="text-center text-slate-400 py-10">加载中...</div>

  return (
    <div>
      {data?.pages.map((page, i) => (
        <Fragment key={i}>
          {page.items.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </Fragment>
      ))}
      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage} className="btn-ghost w-full mt-2">
          {isFetchingNextPage ? '加载中...' : '加载更多'}
        </button>
      )}
      {data && !hasNextPage && data.pages[0].items.length === 0 && (
        <div className="text-center text-slate-400 py-10">还没有动态，发一条吧！</div>
      )}
    </div>
  )
}