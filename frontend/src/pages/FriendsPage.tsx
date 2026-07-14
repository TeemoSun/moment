import { useState, useEffect, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Title, Tabs, Tag, Modal, Input } from "animal-island-ui";
import {
  listFriends,
  listFriendRequests,
  requestFriend,
  acceptFriendRequest,
  rejectFriendRequest,
  removeFriend,
} from "@/api/friends";
import type { FriendOut, FriendRequestOut } from "@/api/friends";
import { ApiError } from "@/api/client";
import { formatRelativeTime } from "@/utils/time";

export default function FriendsPage() {
  const navigate = useNavigate();
  const [friends, setFriends] = useState<FriendOut[]>([]);
  const [requests, setRequests] = useState<FriendRequestOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [email, setEmail] = useState("");
  const [requestMsg, setRequestMsg] = useState("");
  const [requestLoading, setRequestLoading] = useState(false);

  const [removingId, setRemovingId] = useState<number | null>(null);
  const [showRemoveModal, setShowRemoveModal] = useState(false);
  const [removeError, setRemoveError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [friendsData, requestsData] = await Promise.all([
          listFriends(),
          listFriendRequests(),
        ]);
        setFriends(friendsData);
        setRequests(requestsData);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "加载失败");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSendRequest = async () => {
    if (!email.trim()) return;
    setRequestMsg("");
    setRequestLoading(true);
    try {
      await requestFriend({ email: email.trim() });
      setRequestMsg("已发送");
      setEmail("");
    } catch (err) {
      setRequestMsg(err instanceof ApiError ? err.message : "发送失败");
    } finally {
      setRequestLoading(false);
    }
  };

  const handleAccept = async (reqId: number) => {
    try {
      await acceptFriendRequest(reqId);
      setRequests((prev) => prev.filter((r) => r.id !== reqId));
    } catch {
      // ignore
    }
  };

  const handleReject = async (reqId: number) => {
    try {
      await rejectFriendRequest(reqId);
      setRequests((prev) => prev.filter((r) => r.id !== reqId));
    } catch {
      // ignore
    }
  };

  const handleRemoveConfirm = async () => {
    if (removingId === null) return;
    setRemoveError("");
    try {
      await removeFriend(removingId);
      setFriends((prev) => prev.filter((f) => f.user.id !== removingId));
      setShowRemoveModal(false);
      setRemovingId(null);
    } catch (err) {
      setRemoveError(err instanceof ApiError ? err.message : "删除失败");
    }
  };

  const avatarStyle: CSSProperties = {
    width: 50,
    height: 50,
    borderRadius: "50%",
    objectFit: "cover",
    border: "2px solid #c4b89e",
    flexShrink: 0,
    cursor: "pointer",
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

  const friendsTab = (
    <div>
      {friends.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无好友
        </div>
      ) : (
        friends.map((f) => (
          <Card
            key={f.user.id}
            style={{
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <img
              src={f.user.avatar_url}
              alt={f.user.nickname}
              style={avatarStyle}
              onClick={() => navigate(`/users/${f.user.id}`)}
            />
            <div
              style={{ flex: 1, minWidth: 0 }}
              onClick={() => navigate(`/users/${f.user.id}`)}
            >
              <div
                style={{
                  fontWeight: 700,
                  fontSize: 15,
                  color: "#794f27",
                  cursor: "pointer",
                }}
              >
                {f.user.nickname}
              </div>
              <div style={{ color: "#9f927d", fontSize: 13 }}>
                {formatRelativeTime(f.since)}
              </div>
            </div>
            <Tag color="app-teal" size="small">
              好友
            </Tag>
            <Button
              type="default"
              size="small"
              danger
              onClick={() => {
                setRemovingId(f.user.id);
                setShowRemoveModal(true);
              }}
            >
              删除好友
            </Button>
          </Card>
        ))
      )}
    </div>
  );

  const requestsTab = (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: "#794f27", marginBottom: 8 }}>
          添加好友
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <div style={{ flex: 1 }}>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="输入对方邮箱"
            />
          </div>
          <Button
            type="primary"
            size="small"
            onClick={handleSendRequest}
            loading={requestLoading}
          >
            发送请求
          </Button>
        </div>
        {requestMsg && (
          <div
            style={{
              marginTop: 8,
              fontSize: 14,
              fontWeight: 500,
              color: requestMsg === "已发送" ? "#6fba2c" : "#e05a5a",
            }}
          >
            {requestMsg}
          </div>
        )}
      </Card>

      {requests.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无好友请求
        </div>
      ) : (
        requests.map((r) => (
          <Card
            key={r.id}
            style={{
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <img
              src={r.requester.avatar_url}
              alt={r.requester.nickname}
              style={avatarStyle}
              onClick={() => navigate(`/users/${r.requester.id}`)}
            />
            <div
              style={{ flex: 1, minWidth: 0 }}
              onClick={() => navigate(`/users/${r.requester.id}`)}
            >
              <div
                style={{
                  fontWeight: 700,
                  fontSize: 15,
                  color: "#794f27",
                  cursor: "pointer",
                }}
              >
                {r.requester.nickname}
              </div>
              <div style={{ color: "#9f927d", fontSize: 13 }}>
                {formatRelativeTime(r.created_at)}
              </div>
            </div>
            <Button type="primary" size="small" onClick={() => handleAccept(r.id)}>
              接受
            </Button>
            <Button type="default" size="small" danger onClick={() => handleReject(r.id)}>
              拒绝
            </Button>
          </Card>
        ))
      )}
    </div>
  );

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
      <Title color="app-teal" size="middle">
        好友
      </Title>
      <div style={{ marginTop: 16 }}>
        <Tabs
          items={[
            { key: "friends", label: "好友列表", children: friendsTab },
            { key: "requests", label: "好友请求", children: requestsTab },
          ]}
        />
      </div>

      <Modal
        open={showRemoveModal}
        title="确认删除"
        onClose={() => {
          setShowRemoveModal(false);
          setRemovingId(null);
          setRemoveError("");
        }}
        onOk={handleRemoveConfirm}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要删除这位好友吗？</p>
        {removeError && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{removeError}</p>
        )}
      </Modal>
    </div>
  );
}
