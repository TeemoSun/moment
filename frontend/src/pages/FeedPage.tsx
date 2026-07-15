import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Title } from "animal-island-ui";
import { usePostsStore } from "@/stores/posts";
import PostCard from "@/components/PostCard";
import { notify } from "@/utils/notify";

export default function FeedPage() {
  const navigate = useNavigate();
  const { items, hasMore, loading, loadingMore, error, fetchFeed, refresh, removePost } =
    usePostsStore();
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        const state = usePostsStore.getState();
        if (state.items.length > 0 && state.hasMore && !state.loadingMore && !state.loading) {
          state.loadMore();
        }
      }
    });

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  const handleRefresh = async () => {
    await refresh();
    const state = usePostsStore.getState();
    if (state.error) {
      notify.error(state.error);
    } else {
      notify.success("已刷新");
    }
  };

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "24px 16px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <Title color="app-teal" size="middle">
          动态
        </Title>
        <Button type="default" size="small" onClick={handleRefresh} loading={loading}>
          刷新
        </Button>
      </div>

      {loading && items.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 16,
          }}
        >
          加载中...
        </div>
      )}

      {error && items.length === 0 && (
        <div style={{ textAlign: "center", padding: 40 }}>
          <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12 }}>{error}</div>
          <Button type="default" size="small" onClick={() => fetchFeed()}>
            重试
          </Button>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div style={{ textAlign: "center", padding: 40 }}>
          <div style={{ color: "#9f927d", fontWeight: 500, marginBottom: 16, fontSize: 16 }}>
            还没有动态，去发布第一条吧！
          </div>
          <Button type="primary" size="small" onClick={() => navigate("/post/create")}>
            发动态
          </Button>
        </div>
      )}

      {items.map((post) => (
        <PostCard key={post.id} post={post} onDelete={removePost} />
      ))}

      {loadingMore && (
        <div
          style={{
            textAlign: "center",
            padding: 16,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          加载中...
        </div>
      )}

      {!hasMore && items.length > 0 && (
        <div
          style={{
            textAlign: "center",
            padding: 16,
            color: "#c4b89e",
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          没有更多了
        </div>
      )}

      <div ref={sentinelRef} style={{ height: 1 }} />
    </div>
  );
}
