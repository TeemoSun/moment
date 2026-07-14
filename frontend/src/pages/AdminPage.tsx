import { useState, useEffect, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Title, Tabs, Tag, Modal, Input } from "animal-island-ui";
import { ApiError } from "@/api/client";
import {
  getStats,
  listUsers,
  updateUser,
  listPosts,
  deletePost,
  listComments,
  deleteComment,
  listInvites,
  revokeInvite,
} from "@/api/admin";
import type {
  StatsOut,
  AdminUserOut,
  AdminPostOut,
  AdminCommentOut,
  AdminInviteOut,
} from "@/api/admin";
import { formatRelativeTime, parseUTC } from "@/utils/time";
import { notify } from "@/utils/notify";

const avatarStyle: CSSProperties = {
  width: 50,
  height: 50,
  borderRadius: "50%",
  objectFit: "cover",
  border: "2px solid #c4b89e",
  flexShrink: 0,
  cursor: "pointer",
};

const smallAvatarStyle: CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: "50%",
  objectFit: "cover",
  border: "1.5px solid #c4b89e",
  flexShrink: 0,
};

function PaginationBar({
  page,
  hasMore,
  onPageChange,
}: {
  page: number;
  hasMore: boolean;
  onPageChange: (p: number) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        marginTop: 16,
      }}
    >
      <Button
        type="default"
        size="small"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        上一页
      </Button>
      <span style={{ color: "#9f927d", fontSize: 14, fontWeight: 500 }}>第 {page} 页</span>
      <Button
        type="default"
        size="small"
        disabled={!hasMore}
        onClick={() => onPageChange(page + 1)}
      >
        下一页
      </Button>
    </div>
  );
}

export default function AdminPage() {
  const navigate = useNavigate();

  const [stats, setStats] = useState<StatsOut | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState("");

  const [users, setUsers] = useState<AdminUserOut[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersHasMore, setUsersHasMore] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState("");
  const [userSearch, setUserSearch] = useState("");

  const [posts, setPosts] = useState<AdminPostOut[]>([]);
  const [postsTotal, setPostsTotal] = useState(0);
  const [postsPage, setPostsPage] = useState(1);
  const [postsHasMore, setPostsHasMore] = useState(false);
  const [postsLoading, setPostsLoading] = useState(false);
  const [postsError, setPostsError] = useState("");
  const [postsVisibility, setPostsVisibility] = useState("");
  const [postsUserId, setPostsUserId] = useState("");

  const [comments, setComments] = useState<AdminCommentOut[]>([]);
  const [commentsTotal, setCommentsTotal] = useState(0);
  const [commentsPage, setCommentsPage] = useState(1);
  const [commentsHasMore, setCommentsHasMore] = useState(false);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentsError, setCommentsError] = useState("");

  const [invites, setInvites] = useState<AdminInviteOut[]>([]);
  const [invitesTotal, setInvitesTotal] = useState(0);
  const [invitesPage, setInvitesPage] = useState(1);
  const [invitesHasMore, setInvitesHasMore] = useState(false);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [invitesError, setInvitesError] = useState("");

  const [actionLoading, setActionLoading] = useState(false);

  const [activeKey, setActiveKey] = useState("stats");
  const [usersLoaded, setUsersLoaded] = useState(false);
  const [postsLoaded, setPostsLoaded] = useState(false);
  const [commentsLoaded, setCommentsLoaded] = useState(false);
  const [invitesLoaded, setInvitesLoaded] = useState(false);

  const [showUserModal, setShowUserModal] = useState(false);
  const [userModalAction, setUserModalAction] = useState<(() => Promise<unknown>) | null>(null);
  const [userModalTitle, setUserModalTitle] = useState("");
  const [userModalMsg, setUserModalMsg] = useState("");

  const [showDeletePostModal, setShowDeletePostModal] = useState(false);
  const [deletePostId, setDeletePostId] = useState<number | null>(null);
  const [deletePostMsg, setDeletePostMsg] = useState("");

  const [showDeleteCommentModal, setShowDeleteCommentModal] = useState(false);
  const [deleteCommentId, setDeleteCommentId] = useState<number | null>(null);
  const [deleteCommentMsg, setDeleteCommentMsg] = useState("");

  const [showRevokeInviteModal, setShowRevokeInviteModal] = useState(false);
  const [revokeInviteId, setRevokeInviteId] = useState<number | null>(null);
  const [revokeInviteMsg, setRevokeInviteMsg] = useState("");

  useEffect(() => {
    const load = async () => {
      setStatsLoading(true);
      setStatsError("");
      try {
        const data = await getStats();
        setStats(data);
      } catch (err) {
        setStatsError(err instanceof ApiError ? err.message : "加载统计失败");
      } finally {
        setStatsLoading(false);
      }
    };
    load();
  }, []);

  const loadUsers = async (page: number, search?: string) => {
    setUsersLoading(true);
    setUsersError("");
    try {
      const data = await listUsers(search || undefined, page);
      setUsers(data.items);
      setUsersTotal(data.total);
      setUsersPage(data.page);
      setUsersHasMore(data.has_more);
    } catch (err) {
      setUsersError(err instanceof ApiError ? err.message : "加载用户失败");
    } finally {
      setUsersLoading(false);
    }
  };

  const loadPosts = async (page: number, visibility?: string, userId?: string) => {
    setPostsLoading(true);
    setPostsError("");
    try {
      const uid = userId ? parseInt(userId, 10) : undefined;
      const data = await listPosts(
        uid && !isNaN(uid) ? uid : undefined,
        visibility || undefined,
        page,
      );
      setPosts(data.items);
      setPostsTotal(data.total);
      setPostsPage(data.page);
      setPostsHasMore(data.has_more);
    } catch (err) {
      setPostsError(err instanceof ApiError ? err.message : "加载动态失败");
    } finally {
      setPostsLoading(false);
    }
  };

  const loadComments = async (page: number) => {
    setCommentsLoading(true);
    setCommentsError("");
    try {
      const data = await listComments(page);
      setComments(data.items);
      setCommentsTotal(data.total);
      setCommentsPage(data.page);
      setCommentsHasMore(data.has_more);
    } catch (err) {
      setCommentsError(err instanceof ApiError ? err.message : "加载评论失败");
    } finally {
      setCommentsLoading(false);
    }
  };

  const loadInvites = async (page: number) => {
    setInvitesLoading(true);
    setInvitesError("");
    try {
      const data = await listInvites(page);
      setInvites(data.items);
      setInvitesTotal(data.total);
      setInvitesPage(data.page);
      setInvitesHasMore(data.has_more);
    } catch (err) {
      setInvitesError(err instanceof ApiError ? err.message : "加载邀请码失败");
    } finally {
      setInvitesLoading(false);
    }
  };

  const handleUserAction = async () => {
    if (!userModalAction) return;
    setActionLoading(true);
    setUserModalMsg("");
    try {
      await userModalAction();
      notify.success("操作成功");
      setShowUserModal(false);
      setUserModalAction(null);
      loadUsers(usersPage, userSearch);
    } catch (err) {
      setUserModalMsg(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setActionLoading(false);
    }
  };

  const openUserModal = (title: string, action: () => Promise<unknown>) => {
    setUserModalTitle(title);
    setUserModalAction(() => action);
    setUserModalMsg("");
    setShowUserModal(true);
  };

  const handleDeletePostConfirm = async () => {
    if (deletePostId === null) return;
    setActionLoading(true);
    setDeletePostMsg("");
    try {
      await deletePost(deletePostId);
      notify.success("已删除动态");
      setShowDeletePostModal(false);
      setDeletePostId(null);
      loadPosts(postsPage, postsVisibility, postsUserId);
    } catch (err) {
      setDeletePostMsg(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteCommentConfirm = async () => {
    if (deleteCommentId === null) return;
    setActionLoading(true);
    setDeleteCommentMsg("");
    try {
      await deleteComment(deleteCommentId);
      notify.success("已删除评论");
      setShowDeleteCommentModal(false);
      setDeleteCommentId(null);
      loadComments(commentsPage);
    } catch (err) {
      setDeleteCommentMsg(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeInviteConfirm = async () => {
    if (revokeInviteId === null) return;
    setActionLoading(true);
    setRevokeInviteMsg("");
    try {
      await revokeInvite(revokeInviteId);
      notify.success("邀请码已失效");
      setShowRevokeInviteModal(false);
      setRevokeInviteId(null);
      loadInvites(invitesPage);
    } catch (err) {
      setRevokeInviteMsg(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setActionLoading(false);
    }
  };

  const statsTab = (
    <div>
      {statsLoading ? (
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
      ) : statsError ? (
        <div style={{ color: "#e05a5a", fontWeight: 500, textAlign: "center", padding: 40 }}>
          {statsError}
        </div>
      ) : stats ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
            gap: 12,
          }}
        >
          {[
            { label: "用户数", value: stats.user_count },
            { label: "动态数", value: stats.post_count },
            { label: "评论数", value: stats.comment_count },
            { label: "点赞数", value: stats.like_count },
            { label: "邀请码数", value: stats.invite_count },
            { label: "已用邀请码", value: stats.used_invite_count },
          ].map((item) => (
            <Card
              key={item.label}
              style={{
                textAlign: "center",
                padding: "20px 12px",
              }}
            >
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 800,
                  color: "#794f27",
                  lineHeight: 1.2,
                }}
              >
                {item.value}
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: "#9f927d",
                  marginTop: 6,
                }}
              >
                {item.label}
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );

  const usersTab = (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 160 }}>
            <Input
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="搜索邮箱或昵称"
            />
          </div>
          <Button
            type="primary"
            size="small"
            onClick={() => {
              setUsersPage(1);
              loadUsers(1, userSearch);
            }}
            loading={usersLoading}
          >
            搜索
          </Button>
          <Button
            type="default"
            size="small"
            onClick={() => {
              setUserSearch("");
              setUsersPage(1);
              loadUsers(1);
            }}
            loading={usersLoading}
          >
            刷新
          </Button>
        </div>
      </Card>

      {usersError && (
        <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12, fontSize: 14 }}>
          {usersError}
        </div>
      )}

      {(!usersLoaded || usersLoading) && users.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          加载中...
        </div>
      ) : users.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无用户
        </div>
      ) : (
        <>
          {users.map((u) => {
            const isAdmin = u.role === "admin";
            const statusColor =
              u.status === "active"
                ? "app-teal"
                : u.status === "deactivated"
                  ? "app-yellow"
                  : "default";
            const statusLabel =
              u.status === "active"
                ? "正常"
                : u.status === "disabled"
                  ? "已停用"
                  : u.status === "deactivated"
                    ? "已注销"
                    : u.status;
            const roleColor = isAdmin ? "app-yellow" : "app-teal";
            const roleLabel = isAdmin ? "管理员" : "用户";

            return (
              <Card
                key={u.id}
                style={{
                  marginBottom: 8,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <img
                  src={u.avatar_url}
                  alt={u.nickname}
                  style={avatarStyle}
                  onClick={() => navigate(`/users/${u.id}`)}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 700, fontSize: 15, color: "#794f27" }}>
                      {u.nickname}
                    </span>
                    <Tag color={roleColor} size="small">
                      {roleLabel}
                    </Tag>
                    <Tag color={statusColor} size="small">
                      {statusLabel}
                    </Tag>
                  </div>
                  <div style={{ color: "#9f927d", fontSize: 13 }}>{u.email}</div>
                  <div style={{ color: "#9f927d", fontSize: 12, marginTop: 2 }}>
                    注册于 {formatRelativeTime(u.created_at)}
                    {u.last_login_at && ` · 最后登录 ${formatRelativeTime(u.last_login_at)}`}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Button
                    type="default"
                    size="small"
                    onClick={() => {
                      const newCanInvite = !u.can_invite;
                      openUserModal(
                        newCanInvite
                          ? `开启 ${u.nickname} 的邀请权限？`
                          : `关闭 ${u.nickname} 的邀请权限？`,
                        () => updateUser(u.id, { can_invite: newCanInvite }),
                      );
                    }}
                  >
                    邀请:{u.can_invite ? "开" : "关"}
                  </Button>
                  {!isAdmin && u.status === "active" && (
                    <Button
                      type="default"
                      size="small"
                      danger
                      onClick={() => {
                        openUserModal(`确定要停用 ${u.nickname} 吗？`, () =>
                          updateUser(u.id, { status: "disabled" }),
                        );
                      }}
                    >
                      停用
                    </Button>
                  )}
                  {!isAdmin && u.status === "disabled" && (
                    <Button
                      type="default"
                      size="small"
                      onClick={() => {
                        openUserModal(`确定要启用 ${u.nickname} 吗？`, () =>
                          updateUser(u.id, { status: "active" }),
                        );
                      }}
                    >
                      启用
                    </Button>
                  )}
                  {u.status === "deactivated" && (
                    <Button
                      type="default"
                      size="small"
                      onClick={() => {
                        openUserModal(`确定要恢复 ${u.nickname} 的账号吗？`, () =>
                          updateUser(u.id, { restore: true }),
                        );
                      }}
                    >
                      恢复账号
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
          <PaginationBar
            page={usersPage}
            hasMore={usersHasMore}
            onPageChange={(p) => {
              setUsersPage(p);
              loadUsers(p, userSearch);
            }}
          />
          <div
            style={{
              textAlign: "center",
              color: "#9f927d",
              fontSize: 13,
              marginTop: 8,
            }}
          >
            共 {usersTotal} 个用户
          </div>
        </>
      )}
    </div>
  );

  const postsTab = (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={postsVisibility}
            onChange={(e) => setPostsVisibility(e.target.value)}
            style={{
              padding: "6px 12px",
              borderRadius: 8,
              border: "1.5px solid #c4b89e",
              background: "rgb(247, 243, 223)",
              color: "#794f27",
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            <option value="">全部可见性</option>
            <option value="public">公开</option>
            <option value="friends">仅好友</option>
          </select>
          <Input
            value={postsUserId}
            onChange={(e) => setPostsUserId(e.target.value)}
            placeholder="用户ID"
            style={{ width: 100 }}
          />
          <Button
            type="primary"
            size="small"
            onClick={() => {
              setPostsPage(1);
              loadPosts(1, postsVisibility, postsUserId);
            }}
            loading={postsLoading}
          >
            查询
          </Button>
          <Button
            type="default"
            size="small"
            onClick={() => {
              setPostsVisibility("");
              setPostsUserId("");
              setPostsPage(1);
              loadPosts(1);
            }}
            loading={postsLoading}
          >
            刷新
          </Button>
        </div>
      </Card>

      {postsError && (
        <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12, fontSize: 14 }}>
          {postsError}
        </div>
      )}

      {(!postsLoaded || postsLoading) && posts.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          加载中...
        </div>
      ) : posts.length === 0 ? (
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
        <>
          {posts.map((p) => (
            <Card key={p.id} style={{ marginBottom: 8 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 8,
                }}
              >
                <img
                  src={p.author.avatar_url}
                  alt={p.author.nickname}
                  style={smallAvatarStyle}
                  onClick={() => navigate(`/users/${p.author.id}`)}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "#794f27" }}>
                    {p.author.nickname}
                  </div>
                  <div style={{ color: "#9f927d", fontSize: 12 }}>{p.author.email}</div>
                </div>
                <Tag color={p.visibility === "public" ? "app-teal" : "app-yellow"} size="small">
                  {p.visibility === "public" ? "公开" : "仅好友"}
                </Tag>
                {p.deleted && (
                  <Tag color="default" size="small">
                    已删除
                  </Tag>
                )}
              </div>
              <div
                style={{
                  color: "#725d42",
                  fontSize: 14,
                  marginBottom: 8,
                  cursor: p.deleted ? "default" : "pointer",
                  wordBreak: "break-word",
                }}
                onClick={() => {
                  if (!p.deleted) navigate(`/posts/${p.id}`);
                }}
              >
                {p.content || "(无文字内容)"}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 8,
                }}
              >
                <div style={{ color: "#9f927d", fontSize: 12 }}>
                  {formatRelativeTime(p.created_at)}
                  {p.deleted_at && (
                    <span style={{ color: "#e05a5a", marginLeft: 8 }}>
                      删除于 {formatRelativeTime(p.deleted_at)}
                    </span>
                  )}
                  <span style={{ marginLeft: 12 }}>
                    点赞 {p.like_count} · 评论 {p.comment_count}
                  </span>
                </div>
                {!p.deleted && (
                  <Button
                    type="default"
                    size="small"
                    danger
                    onClick={() => {
                      setDeletePostId(p.id);
                      setDeletePostMsg("");
                      setShowDeletePostModal(true);
                    }}
                  >
                    删除动态
                  </Button>
                )}
              </div>
            </Card>
          ))}
          <PaginationBar
            page={postsPage}
            hasMore={postsHasMore}
            onPageChange={(p) => {
              setPostsPage(p);
              loadPosts(p, postsVisibility, postsUserId);
            }}
          />
          <div
            style={{
              textAlign: "center",
              color: "#9f927d",
              fontSize: 13,
              marginTop: 8,
            }}
          >
            共 {postsTotal} 条动态
          </div>
        </>
      )}
    </div>
  );

  const commentsTab = (
    <div>
      {commentsError && (
        <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12, fontSize: 14 }}>
          {commentsError}
        </div>
      )}

      {(!commentsLoaded || commentsLoading) && comments.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          加载中...
        </div>
      ) : comments.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无评论
        </div>
      ) : (
        <>
          {comments.map((c) => (
            <Card key={c.id} style={{ marginBottom: 8 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 8,
                }}
              >
                <img
                  src={c.author.avatar_url}
                  alt={c.author.nickname}
                  style={smallAvatarStyle}
                  onClick={() => navigate(`/users/${c.author.id}`)}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "#794f27" }}>
                    {c.author.nickname}
                  </div>
                  <div style={{ color: "#9f927d", fontSize: 12 }}>{c.author.email}</div>
                </div>
                {c.deleted && (
                  <Tag color="default" size="small">
                    已删除
                  </Tag>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 8,
                }}
              >
                {c.image_thumb_url ? (
                  <img
                    src={c.image_thumb_url}
                    alt="评论图片"
                    style={{
                      width: 60,
                      height: 60,
                      objectFit: "cover",
                      borderRadius: 8,
                      border: "1.5px solid #c4b89e",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      color: "#725d42",
                      fontSize: 14,
                      wordBreak: "break-word",
                      flex: 1,
                    }}
                  >
                    {c.content || "(无内容)"}
                  </div>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 8,
                }}
              >
                <div style={{ color: "#9f927d", fontSize: 12 }}>
                  <span
                    style={{ cursor: "pointer", color: "#794f27", fontWeight: 500 }}
                    onClick={() => navigate(`/posts/${c.post_id}`)}
                  >
                    动态 #{c.post_id}
                  </span>
                  <span style={{ marginLeft: 12 }}>点赞 {c.like_count}</span>
                  <span style={{ marginLeft: 12 }}>{formatRelativeTime(c.created_at)}</span>
                </div>
                {!c.deleted && (
                  <Button
                    type="default"
                    size="small"
                    danger
                    onClick={() => {
                      setDeleteCommentId(c.id);
                      setDeleteCommentMsg("");
                      setShowDeleteCommentModal(true);
                    }}
                  >
                    删除评论
                  </Button>
                )}
              </div>
            </Card>
          ))}
          <PaginationBar
            page={commentsPage}
            hasMore={commentsHasMore}
            onPageChange={(p) => {
              setCommentsPage(p);
              loadComments(p);
            }}
          />
          <div
            style={{
              textAlign: "center",
              color: "#9f927d",
              fontSize: 13,
              marginTop: 8,
            }}
          >
            共 {commentsTotal} 条评论
          </div>
        </>
      )}
    </div>
  );

  const invitesTab = (
    <div>
      {invitesError && (
        <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12, fontSize: 14 }}>
          {invitesError}
        </div>
      )}

      {(!invitesLoaded || invitesLoading) && invites.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          加载中...
        </div>
      ) : invites.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无邀请码
        </div>
      ) : (
        <>
          {invites.map((inv) => {
            const statusColor =
              inv.status === "active"
                ? "app-teal"
                : inv.status === "used"
                  ? "app-yellow"
                  : "default";
            const statusLabel =
              inv.status === "active"
                ? "有效"
                : inv.status === "used"
                  ? "已使用"
                  : inv.status === "expired"
                    ? "已过期"
                    : inv.status === "revoked"
                      ? "已失效"
                      : inv.status;

            return (
              <Card key={inv.id} style={{ marginBottom: 8 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    marginBottom: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontWeight: 700,
                      fontSize: 16,
                      color: "#794f27",
                    }}
                  >
                    {inv.code}
                  </span>
                  <Tag color={statusColor} size="small">
                    {statusLabel}
                  </Tag>
                  <span style={{ color: "#9f927d", fontSize: 12 }}>
                    {inv.expires_at
                      ? `过期: ${parseUTC(inv.expires_at).toLocaleDateString()}`
                      : "永久"}
                  </span>
                  {inv.status === "active" && (
                    <Button
                      type="default"
                      size="small"
                      danger
                      style={{ marginLeft: "auto" }}
                      onClick={() => {
                        setRevokeInviteId(inv.id);
                        setRevokeInviteMsg("");
                        setShowRevokeInviteModal(true);
                      }}
                    >
                      失效
                    </Button>
                  )}
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                  }}
                >
                  <img
                    src={inv.creator.avatar_url}
                    alt={inv.creator.nickname}
                    style={smallAvatarStyle}
                    onClick={() => navigate(`/users/${inv.creator.id}`)}
                  />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: "#794f27" }}>
                      {inv.creator.nickname}
                    </div>
                    <div style={{ color: "#9f927d", fontSize: 12 }}>{inv.creator.email}</div>
                  </div>
                  {inv.used_by_id !== null && (
                    <span style={{ color: "#9f927d", fontSize: 12, marginLeft: "auto" }}>
                      使用者 ID: {inv.used_by_id}
                    </span>
                  )}
                </div>
                <div style={{ color: "#9f927d", fontSize: 12, marginTop: 6 }}>
                  创建: {formatRelativeTime(inv.created_at)}
                </div>
              </Card>
            );
          })}
          <PaginationBar
            page={invitesPage}
            hasMore={invitesHasMore}
            onPageChange={(p) => {
              setInvitesPage(p);
              loadInvites(p);
            }}
          />
          <div
            style={{
              textAlign: "center",
              color: "#9f927d",
              fontSize: 13,
              marginTop: 8,
            }}
          >
            共 {invitesTotal} 个邀请码
          </div>
        </>
      )}
    </div>
  );

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
      <Title color="app-teal">管理后台</Title>
      <div style={{ marginTop: 16 }}>
        <Tabs
          activeKey={activeKey}
          onChange={(key) => {
            setActiveKey(key);
            if (key === "users" && !usersLoaded) {
              setUsersLoaded(true);
              loadUsers(1);
            } else if (key === "posts" && !postsLoaded) {
              setPostsLoaded(true);
              loadPosts(1);
            } else if (key === "comments" && !commentsLoaded) {
              setCommentsLoaded(true);
              loadComments(1);
            } else if (key === "invites" && !invitesLoaded) {
              setInvitesLoaded(true);
              loadInvites(1);
            }
          }}
          items={[
            { key: "stats", label: "统计", children: statsTab },
            {
              key: "users",
              label: "用户管理",
              children: usersTab,
            },
            {
              key: "posts",
              label: "动态管理",
              children: postsTab,
            },
            {
              key: "comments",
              label: "评论管理",
              children: commentsTab,
            },
            {
              key: "invites",
              label: "邀请码管理",
              children: invitesTab,
            },
          ]}
        />
      </div>

      <Modal
        open={showUserModal}
        title={userModalTitle}
        onClose={() => {
          setShowUserModal(false);
          setUserModalAction(null);
          setUserModalMsg("");
        }}
        onOk={handleUserAction}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要执行此操作吗？</p>
        {userModalMsg && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{userModalMsg}</p>
        )}
        {actionLoading && (
          <p style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>处理中...</p>
        )}
      </Modal>

      <Modal
        open={showDeletePostModal}
        title="确认删除动态"
        onClose={() => {
          setShowDeletePostModal(false);
          setDeletePostId(null);
          setDeletePostMsg("");
        }}
        onOk={handleDeletePostConfirm}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要删除这条动态吗？此操作不可撤销。</p>
        {deletePostMsg && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{deletePostMsg}</p>
        )}
        {actionLoading && (
          <p style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>删除中...</p>
        )}
      </Modal>

      <Modal
        open={showDeleteCommentModal}
        title="确认删除评论"
        onClose={() => {
          setShowDeleteCommentModal(false);
          setDeleteCommentId(null);
          setDeleteCommentMsg("");
        }}
        onOk={handleDeleteCommentConfirm}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要删除这条评论吗？此操作不可撤销。</p>
        {deleteCommentMsg && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{deleteCommentMsg}</p>
        )}
        {actionLoading && (
          <p style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>删除中...</p>
        )}
      </Modal>

      <Modal
        open={showRevokeInviteModal}
        title="确认使邀请码失效"
        onClose={() => {
          setShowRevokeInviteModal(false);
          setRevokeInviteId(null);
          setRevokeInviteMsg("");
        }}
        onOk={handleRevokeInviteConfirm}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要使此邀请码失效吗？此操作不可撤销。</p>
        {revokeInviteMsg && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{revokeInviteMsg}</p>
        )}
        {actionLoading && (
          <p style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>处理中...</p>
        )}
      </Modal>
    </div>
  );
}
