import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Card, Tag, Modal, Input } from "animal-island-ui";
import { getUser } from "@/api/me";
import type { OtherUserOut } from "@/api/me";
import type { PostOut } from "@/api/posts";
import { getUserPosts } from "@/api/posts";
import { ApiError } from "@/api/client";
import PostCard from "@/components/PostCard";
import {
  requestFriend,
  acceptFriendRequest,
  rejectFriendRequest,
  removeFriend,
  listFriendRequests,
} from "@/api/friends";

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

  const [friendMsg, setFriendMsg] = useState("");
  const [friendLoading, setFriendLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showRemoveModal, setShowRemoveModal] = useState(false);
  const [friendEmail, setFriendEmail] = useState("");

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

  const reloadUser = async () => {
    try {
      const userData = await getUser(userIdNum);
      setUser(userData);
    } catch {
      // ignore
    }
  };

  const handleSendFriendRequest = async () => {
    if (!friendEmail.trim()) return;
    setFriendMsg("");
    setFriendLoading(true);
    try {
      await requestFriend({ email: friendEmail.trim() });
      setFriendMsg("已发送");
      setFriendEmail("");
      setShowAddModal(false);
      await reloadUser();
    } catch (err) {
      setFriendMsg(err instanceof ApiError ? err.message : "发送失败");
    } finally {
      setFriendLoading(false);
    }
  };

  const handleAcceptFriend = async () => {
    if (!user) return;
    setFriendLoading(true);
    setFriendMsg("");
    try {
      const reqs = await listFriendRequests();
      const req = reqs.find((r) => r.requester.id === user.id);
      if (!req) {
        setFriendMsg("未找到好友请求");
        setFriendLoading(false);
        return;
      }
      await acceptFriendRequest(req.id);
      setFriendMsg("已接受");
      await reloadUser();
    } catch (err) {
      setFriendMsg(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setFriendLoading(false);
    }
  };

  const handleRejectFriend = async () => {
    if (!user) return;
    setFriendLoading(true);
    setFriendMsg("");
    try {
      const reqs = await listFriendRequests();
      const req = reqs.find((r) => r.requester.id === user.id);
      if (!req) {
        setFriendMsg("未找到好友请求");
        setFriendLoading(false);
        return;
      }
      await rejectFriendRequest(req.id);
      setFriendMsg("已拒绝");
      await reloadUser();
    } catch (err) {
      setFriendMsg(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setFriendLoading(false);
    }
  };

  const handleRemoveFriend = async () => {
    if (!user) return;
    setFriendLoading(true);
    setFriendMsg("");
    try {
      await removeFriend(user.id);
      setFriendMsg("已删除好友");
      setShowRemoveModal(false);
      await reloadUser();
    } catch (err) {
      setFriendMsg(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setFriendLoading(false);
    }
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

      {user.friendship_status !== "self" && !user.is_deactivated && (
        <Card style={{ marginTop: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {user.friendship_status === "none" && (
              <Button
                type="primary"
                size="small"
                onClick={() => setShowAddModal(true)}
                loading={friendLoading}
              >
                加好友
              </Button>
            )}
            {user.friendship_status === "pending_sent" && (
              <Tag color="app-yellow" size="small" variant="solid">
                待对方确认
              </Tag>
            )}
            {user.friendship_status === "pending_received" && (
              <>
                <Button
                  type="primary"
                  size="small"
                  onClick={handleAcceptFriend}
                  loading={friendLoading}
                >
                  接受好友
                </Button>
                <Button
                  type="default"
                  size="small"
                  danger
                  onClick={handleRejectFriend}
                  loading={friendLoading}
                >
                  拒绝
                </Button>
              </>
            )}
            {user.friendship_status === "friends" && (
              <Button
                type="default"
                size="small"
                danger
                onClick={() => setShowRemoveModal(true)}
                loading={friendLoading}
              >
                删除好友
              </Button>
            )}
            {user.friendship_status === "self" && (
              <Tag color="app-teal" size="small">
                这是你
              </Tag>
            )}
          </div>
          {friendMsg && (
            <div
              style={{
                marginTop: 8,
                fontSize: 14,
                fontWeight: 500,
                color:
                  friendMsg === "已发送" || friendMsg === "已接受" || friendMsg === "已删除好友"
                    ? "#6fba2c"
                    : "#e05a5a",
              }}
            >
              {friendMsg}
            </div>
          )}
        </Card>
      )}

      {user.friendship_status === "self" && (
        <Card style={{ marginTop: 12 }}>
          <Tag color="app-teal" size="small">
            这是你
          </Tag>
        </Card>
      )}

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

      <Modal
        open={showAddModal}
        title="加好友"
        onClose={() => {
          setShowAddModal(false);
          setFriendMsg("");
          setFriendEmail("");
        }}
        onOk={handleSendFriendRequest}
        typewriter={false}
      >
        <div style={{ marginBottom: 8 }}>请输入对方邮箱：</div>
        <Input
          value={friendEmail}
          onChange={(e) => setFriendEmail(e.target.value)}
          placeholder="对方邮箱"
        />
        {friendMsg && (
          <div
            style={{
              marginTop: 8,
              fontSize: 14,
              fontWeight: 500,
              color: friendMsg === "已发送" ? "#6fba2c" : "#e05a5a",
            }}
          >
            {friendMsg}
          </div>
        )}
      </Modal>

      <Modal
        open={showRemoveModal}
        title="确认删除"
        onClose={() => {
          setShowRemoveModal(false);
          setFriendMsg("");
        }}
        onOk={handleRemoveFriend}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要删除这位好友吗？</p>
        {friendMsg && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{friendMsg}</p>
        )}
      </Modal>
    </div>
  );
}
