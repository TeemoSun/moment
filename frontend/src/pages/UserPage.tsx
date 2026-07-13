import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Card } from "animal-island-ui";
import { getUser } from "@/api/me";
import type { OtherUserOut } from "@/api/me";
import type { PostOut } from "@/api/posts";
import { getUserPosts } from "@/api/posts";
import { ApiError } from "@/api/client";
import PostCard from "@/components/PostCard";

export default function UserPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const userIdNum = Number(userId);

  const [user, setUser] = useState<OtherUserOut | null>(null);
  const [posts, setPosts] = useState<PostOut[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!userIdNum || isNaN(userIdNum)) return;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [userData, postsData] = await Promise.all([
          getUser(userIdNum),
          getUserPosts(userIdNum),
        ]);
        setUser(userData);
        setPosts(postsData.items);
        setNextCursor(postsData.next_cursor);
        setHasMore(postsData.has_more);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "加载失败");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [userIdNum]);

  const handleLoadMoreRef = useRef(async () => {});
  handleLoadMoreRef.current = async () => {
    if (!nextCursor || loadingMore || !userIdNum) return;
    setLoadingMore(true);
    try {
      const res = await getUserPosts(userIdNum, nextCursor);
      setPosts((prev) => [...prev, ...res.items]);
      setNextCursor(res.next_cursor);
      setHasMore(res.has_more);
    } catch {
      // ignore
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        if (posts.length > 0 && hasMore && !loadingMore && !loading) {
          handleLoadMoreRef.current();
        }
      }
    });

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [posts.length, hasMore, loadingMore, loading]);

  const handleRemovePost = (id: number) => {
    setPosts((prev) => prev.filter((p) => p.id !== id));
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
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
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
        <div style={{ textAlign: "center", padding: 40 }}>
          <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12 }}>{error}</div>
          <Button type="default" size="small" onClick={() => navigate(-1)}>
            返回
          </Button>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
      <Button type="default" size="small" onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <img
          src={user.avatar_url}
          alt={user.nickname}
          style={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            objectFit: "cover",
            border: "2.5px solid #c4b89e",
          }}
        />
        <div>
          <div style={{ fontWeight: 700, fontSize: 18, color: "#794f27" }}>{user.nickname}</div>
          {user.signature && (
            <div style={{ color: "#8a7b66", fontSize: 14, marginTop: 4 }}>{user.signature}</div>
          )}
        </div>
      </Card>

      <div style={{ marginTop: 24 }}>
        {posts.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: 40,
              color: "#9f927d",
              fontWeight: 500,
              fontSize: 15,
            }}
          >
            暂无动态
          </div>
        ) : (
          posts.map((post) => <PostCard key={post.id} post={post} onDelete={handleRemovePost} />)
        )}
      </div>

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

      {!hasMore && posts.length > 0 && (
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
