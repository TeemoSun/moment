import { useState, useEffect, useRef, type CSSProperties } from "react";
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
  getLLMConfig,
  updateLLMConfig,
  testLLMConfig,
} from "@/api/admin";
import type {
  StatsOut,
  AdminUserOut,
  AdminPostOut,
  AdminCommentOut,
  AdminInviteOut,
  LLMConfigOut,
  LLMConfigUpdateIn,
  LLMConfigTestIn,
} from "@/api/admin";
import {
  listBotsAdmin,
  createBot,
  updateBot,
  deleteBot,
  uploadBotAvatar,
  triggerBotNow,
} from "@/api/bots";
import type { BotAdminOut, BotCreateIn, BotUpdateIn } from "@/api/bots";
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

  const [bots, setBots] = useState<BotAdminOut[]>([]);
  const [botsLoaded, setBotsLoaded] = useState(false);
  const [botsLoading, setBotsLoading] = useState(false);
  const [botsError, setBotsError] = useState("");

  const [showCreateBotModal, setShowCreateBotModal] = useState(false);
  const [showEditBotModal, setShowEditBotModal] = useState(false);
  const [showDeleteBotModal, setShowDeleteBotModal] = useState(false);
  const [editingBot, setEditingBot] = useState<BotAdminOut | null>(null);
  const [deletingBotId, setDeletingBotId] = useState<number | null>(null);
  const [botModalError, setBotModalError] = useState("");
  const [botModalLoading, setBotModalLoading] = useState(false);

  const [newBot, setNewBot] = useState<BotCreateIn>({
    nickname: "",
    persona: "",
    poll_interval_n: 600,
    poll_interval_x: 60,
    lookback_days: 3,
    comments_per_hour: 10,
    max_consecutive_failures: 5,
    llm_model: "",
  });

  const [editBot, setEditBot] = useState<BotUpdateIn>({});

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingBotId, setUploadingBotId] = useState<number | null>(null);

  const [actionLoading, setActionLoading] = useState(false);

  const [llmConfig, setLlmConfig] = useState<LLMConfigOut | null>(null);
  const [llmLoaded, setLlmLoaded] = useState(false);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmError, setLlmError] = useState("");
  const [llmForm, setLlmForm] = useState<LLMConfigUpdateIn>({});
  const [llmApiKeyInput, setLlmApiKeyInput] = useState("");
  const [llmApiKeyTouched, setLlmApiKeyTouched] = useState(false);
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmTesting, setLlmTesting] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<string>("");

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

  const loadBots = async () => {
    setBotsLoading(true);
    setBotsError("");
    try {
      const data = await listBotsAdmin();
      setBots(data);
    } catch (err) {
      setBotsError(err instanceof ApiError ? err.message : "加载机器人列表失败");
    } finally {
      setBotsLoading(false);
    }
  };

  const loadLLMConfig = async () => {
    setLlmLoading(true);
    setLlmError("");
    try {
      const data = await getLLMConfig();
      setLlmConfig(data);
      setLlmForm({
        base_url: data.base_url,
        model: data.model,
        timeout: data.timeout,
        max_tokens: data.max_tokens,
      });
      setLlmApiKeyInput("");
      setLlmApiKeyTouched(false);
    } catch (err) {
      setLlmError(err instanceof ApiError ? err.message : "加载大模型配置失败");
    } finally {
      setLlmLoading(false);
    }
  };

  const handleSaveLLMConfig = async () => {
    setLlmSaving(true);
    setLlmError("");
    try {
      const data: LLMConfigUpdateIn = {};
      if (llmForm.base_url !== undefined) data.base_url = llmForm.base_url.trim();
      if (llmForm.model !== undefined) data.model = llmForm.model.trim();
      if (llmForm.timeout !== undefined) data.timeout = llmForm.timeout;
      if (llmForm.max_tokens !== undefined) data.max_tokens = llmForm.max_tokens;
      if (llmApiKeyTouched) data.api_key = llmApiKeyInput;
      const result = await updateLLMConfig(data);
      setLlmConfig(result);
      setLlmApiKeyInput("");
      setLlmApiKeyTouched(false);
      notify.success("大模型配置已保存");
    } catch (err) {
      setLlmError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setLlmSaving(false);
    }
  };

  const handleTestLLMConfig = async () => {
    setLlmTesting(true);
    setLlmTestResult("");
    try {
      const data: LLMConfigTestIn = {};
      if (llmForm.base_url) data.base_url = llmForm.base_url.trim();
      if (llmForm.model) data.model = llmForm.model.trim();
      if (llmForm.timeout) data.timeout = llmForm.timeout;
      if (llmForm.max_tokens) data.max_tokens = llmForm.max_tokens;
      if (llmApiKeyTouched) data.api_key = llmApiKeyInput;
      const result = await testLLMConfig(data);
      setLlmTestResult(result.message);
      if (result.success) notify.success("测试成功");
      else notify.error("测试失败");
    } catch (err) {
      setLlmTestResult(err instanceof ApiError ? err.message : "测试失败");
      notify.error("测试失败");
    } finally {
      setLlmTesting(false);
    }
  };

  const handleCreateBot = async () => {
    if (!newBot.nickname.trim() || !newBot.persona.trim()) {
      setBotModalError("昵称和人设不能为空");
      return;
    }
    setBotModalLoading(true);
    setBotModalError("");
    try {
      const data: BotCreateIn = {
        nickname: newBot.nickname.trim(),
        persona: newBot.persona.trim(),
      };
      if (newBot.poll_interval_n !== undefined) data.poll_interval_n = newBot.poll_interval_n;
      if (newBot.poll_interval_x !== undefined) data.poll_interval_x = newBot.poll_interval_x;
      if (newBot.lookback_days !== undefined) data.lookback_days = newBot.lookback_days;
      if (newBot.comments_per_hour !== undefined) data.comments_per_hour = newBot.comments_per_hour;
      if (newBot.max_consecutive_failures !== undefined)
        data.max_consecutive_failures = newBot.max_consecutive_failures;
      if (newBot.llm_model && newBot.llm_model.trim()) data.llm_model = newBot.llm_model.trim();
      await createBot(data);
      notify.success("机器人已创建");
      setShowCreateBotModal(false);
      setNewBot({
        nickname: "",
        persona: "",
        poll_interval_n: 600,
        poll_interval_x: 60,
        lookback_days: 3,
        comments_per_hour: 10,
        max_consecutive_failures: 5,
        llm_model: "",
      });
      await loadBots();
    } catch (err) {
      setBotModalError(err instanceof ApiError ? err.message : "创建失败");
    } finally {
      setBotModalLoading(false);
    }
  };

  const handleUpdateBot = async () => {
    if (!editingBot) return;
    if (editBot.nickname !== undefined && !editBot.nickname.trim()) {
      setBotModalError("昵称不能为空");
      return;
    }
    if (editBot.persona !== undefined && !editBot.persona.trim()) {
      setBotModalError("人设不能为空");
      return;
    }
    setBotModalLoading(true);
    setBotModalError("");
    try {
      const data: BotUpdateIn = {};
      if (editBot.nickname !== undefined) data.nickname = editBot.nickname.trim();
      if (editBot.persona !== undefined) data.persona = editBot.persona.trim();
      if (editBot.poll_interval_n !== undefined) data.poll_interval_n = editBot.poll_interval_n;
      if (editBot.poll_interval_x !== undefined) data.poll_interval_x = editBot.poll_interval_x;
      if (editBot.lookback_days !== undefined) data.lookback_days = editBot.lookback_days;
      if (editBot.comments_per_hour !== undefined)
        data.comments_per_hour = editBot.comments_per_hour;
      if (editBot.max_consecutive_failures !== undefined)
        data.max_consecutive_failures = editBot.max_consecutive_failures;
      if (editBot.llm_model !== undefined) data.llm_model = editBot.llm_model;
      if (editBot.enabled !== undefined) data.enabled = editBot.enabled;
      if (editBot.restore !== undefined) data.restore = editBot.restore;
      await updateBot(editingBot.id, data);
      notify.success("机器人已更新");
      setShowEditBotModal(false);
      setEditingBot(null);
      setEditBot({});
      await loadBots();
    } catch (err) {
      setBotModalError(err instanceof ApiError ? err.message : "更新失败");
    } finally {
      setBotModalLoading(false);
    }
  };

  const handleDeleteBot = async () => {
    if (deletingBotId === null) return;
    setBotModalLoading(true);
    setBotModalError("");
    try {
      await deleteBot(deletingBotId);
      notify.success("机器人已停用");
      setShowDeleteBotModal(false);
      setDeletingBotId(null);
      await loadBots();
    } catch (err) {
      setBotModalError(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setBotModalLoading(false);
    }
  };

  const handleToggleBotEnabled = async (bot: BotAdminOut) => {
    try {
      await updateBot(bot.id, { enabled: !bot.enabled });
      notify.success(bot.enabled ? "机器人已停用" : "机器人已启用");
      await loadBots();
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  const handleRestoreBot = async (bot: BotAdminOut) => {
    try {
      await updateBot(bot.id, { restore: true });
      notify.success("机器人已恢复");
      await loadBots();
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  const handleTriggerBot = async (bot: BotAdminOut) => {
    try {
      await triggerBotNow(bot.id);
      notify.success("已触发轮询");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  const handleUploadBotAvatar = async (botId: number, file: File) => {
    setUploadingBotId(botId);
    try {
      await uploadBotAvatar(botId, file);
      notify.success("头像已更新");
      await loadBots();
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "上传失败");
    } finally {
      setUploadingBotId(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const openEditBotModal = (bot: BotAdminOut) => {
    setEditingBot(bot);
    setEditBot({
      nickname: bot.nickname,
      persona: bot.persona,
      poll_interval_n: bot.poll_interval_n,
      poll_interval_x: bot.poll_interval_x,
      lookback_days: bot.lookback_days,
      comments_per_hour: bot.comments_per_hour,
      max_consecutive_failures: bot.max_consecutive_failures,
      llm_model: bot.llm_model || "",
    });
    setBotModalError("");
    setShowEditBotModal(true);
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

  const botsTab = (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          size="small"
          onClick={() => {
            setBotModalError("");
            setShowCreateBotModal(true);
          }}
        >
          创建机器人
        </Button>
      </Card>

      {botsError && (
        <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12, fontSize: 14 }}>
          {botsError}
        </div>
      )}

      {!botsLoaded || botsLoading ? (
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
      ) : bots.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无机器人
        </div>
      ) : (
        bots.map((bot) => (
          <Card key={bot.id} style={{ marginBottom: 8 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginBottom: 12,
              }}
            >
              <img
                src={bot.avatar_url}
                alt={bot.nickname}
                style={avatarStyle}
                onClick={() => navigate(`/users/${bot.user_id}`)}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontWeight: 700, fontSize: 15, color: "#794f27" }}>
                    {bot.nickname}
                  </span>
                  <Tag color={bot.enabled ? "app-teal" : "default"} size="small">
                    {bot.enabled ? "启用" : "停用"}
                  </Tag>
                  {bot.auto_paused && (
                    <Tag color="app-yellow" size="small">
                      自动暂停
                    </Tag>
                  )}
                </div>
                <div style={{ color: "#9f927d", fontSize: 13 }}>{bot.email}</div>
              </div>
            </div>

            <div
              style={{
                color: "#725d42",
                fontSize: 13,
                marginBottom: 8,
                wordBreak: "break-word",
              }}
            >
              {bot.persona.length > 100 ? `${bot.persona.substring(0, 100)}...` : bot.persona}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                gap: 8,
                marginBottom: 12,
                fontSize: 12,
                color: "#9f927d",
              }}
            >
              <div>
                间隔: {bot.poll_interval_n}s / {bot.poll_interval_x}
              </div>
              <div>限频: {bot.comments_per_hour}/h</div>
              <div>回看: {bot.lookback_days}天</div>
              <div>最大失败: {bot.max_consecutive_failures}</div>
              {bot.llm_model && <div>模型: {bot.llm_model}</div>}
              <div>连续失败: {bot.consecutive_failures}</div>
              {bot.last_run_at && <div>上次: {formatRelativeTime(bot.last_run_at)}</div>}
              {bot.next_run_at && <div>下次: {formatRelativeTime(bot.next_run_at)}</div>}
            </div>

            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Button type="default" size="small" onClick={() => openEditBotModal(bot)}>
                编辑
              </Button>
              <Button type="default" size="small" onClick={() => handleToggleBotEnabled(bot)}>
                {bot.enabled ? "停用" : "启用"}
              </Button>
              {bot.auto_paused && (
                <Button type="default" size="small" onClick={() => handleRestoreBot(bot)}>
                  恢复
                </Button>
              )}
              <Button type="default" size="small" onClick={() => handleTriggerBot(bot)}>
                立即执行
              </Button>
              <Button
                type="default"
                size="small"
                loading={uploadingBotId === bot.id}
                onClick={() => {
                  if (fileInputRef.current) {
                    fileInputRef.current.setAttribute("data-bot-id", String(bot.id));
                    fileInputRef.current.click();
                  }
                }}
              >
                上传头像
              </Button>
              <Button
                type="default"
                size="small"
                danger
                onClick={() => {
                  setDeletingBotId(bot.id);
                  setBotModalError("");
                  setShowDeleteBotModal(true);
                }}
              >
                停用
              </Button>
            </div>
          </Card>
        ))
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          const botId = e.target.getAttribute("data-bot-id");
          if (file && botId) {
            handleUploadBotAvatar(parseInt(botId, 10), file);
          }
        }}
      />
    </div>
  );

  const llmConfigTab = (
    <div>
      {llmError && (
        <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12, fontSize: 14 }}>
          {llmError}
        </div>
      )}

      {!llmLoaded || llmLoading ? (
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
      ) : llmConfig ? (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
                API Base URL
              </div>
              <Input
                value={llmForm.base_url || ""}
                onChange={(e) => setLlmForm({ ...llmForm, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
                API Key{" "}
                {!llmApiKeyTouched && llmConfig.has_api_key ? (
                  <span style={{ color: "#9f927d", fontSize: 12, fontWeight: 500 }}>
                    （已配置，输入新值可替换）
                  </span>
                ) : null}
              </div>
              <Input
                value={llmApiKeyInput}
                onChange={(e) => {
                  setLlmApiKeyInput(e.target.value);
                  setLlmApiKeyTouched(true);
                }}
                placeholder={llmConfig.has_api_key ? "••••••（留空则不变）" : "请输入 API Key"}
              />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
                默认模型
              </div>
              <Input
                value={llmForm.model || ""}
                onChange={(e) => setLlmForm({ ...llmForm, model: e.target.value })}
                placeholder="gpt-4o-mini"
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <div>
                <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>超时(秒)</div>
                <Input
                  type="number"
                  value={llmForm.timeout}
                  onChange={(e) =>
                    setLlmForm({
                      ...llmForm,
                      timeout: parseInt(e.target.value, 10) || 30,
                    })
                  }
                />
              </div>
              <div>
                <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>最大 Tokens</div>
                <Input
                  type="number"
                  value={llmForm.max_tokens}
                  onChange={(e) =>
                    setLlmForm({
                      ...llmForm,
                      max_tokens: parseInt(e.target.value, 10) || 300,
                    })
                  }
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Button type="primary" size="small" loading={llmSaving} onClick={handleSaveLLMConfig}>
                保存配置
              </Button>
              <Button
                type="default"
                size="small"
                loading={llmTesting}
                onClick={handleTestLLMConfig}
              >
                测试连通性
              </Button>
            </div>
            {llmTestResult && (
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  padding: "10px 12px",
                  borderRadius: 8,
                  background: "rgb(247, 243, 223)",
                  color: llmTestResult.startsWith("测试成功") ? "#5a9e1e" : "#e05a5a",
                  wordBreak: "break-word",
                }}
              >
                {llmTestResult}
              </div>
            )}
            <div style={{ color: "#9f927d", fontSize: 12, marginTop: 4 }}>
              说明：此配置全局生效，所有机器人在未单独指定模型时使用上述默认模型。
            </div>
          </div>
        </Card>
      ) : null}
    </div>
  );

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 16px" }}>
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
            } else if (key === "bots" && !botsLoaded) {
              setBotsLoaded(true);
              loadBots();
            } else if (key === "llm-config" && !llmLoaded) {
              setLlmLoaded(true);
              loadLLMConfig();
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
            {
              key: "bots",
              label: "机器人管理",
              children: botsTab,
            },
            {
              key: "llm-config",
              label: "大模型配置",
              children: llmConfigTab,
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

      <Modal
        open={showCreateBotModal}
        title="创建机器人"
        onClose={() => {
          setShowCreateBotModal(false);
          setBotModalError("");
        }}
        onOk={handleCreateBot}
        typewriter={false}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
              昵称
            </div>
            <Input
              value={newBot.nickname}
              onChange={(e) => setNewBot({ ...newBot, nickname: e.target.value })}
              placeholder="机器人昵称"
            />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
              人设
            </div>
            <textarea
              value={newBot.persona}
              onChange={(e) => setNewBot({ ...newBot, persona: e.target.value })}
              placeholder="机器人人设描述"
              rows={4}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: 8,
                border: "1.5px solid #c4b89e",
                background: "rgb(247, 243, 223)",
                color: "#794f27",
                fontSize: 14,
                fontFamily: "inherit",
                resize: "vertical",
              }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>轮询间隔(秒)</div>
              <Input
                type="number"
                value={newBot.poll_interval_n}
                onChange={(e) =>
                  setNewBot({ ...newBot, poll_interval_n: parseInt(e.target.value, 10) || 600 })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>随机偏移</div>
              <Input
                type="number"
                value={newBot.poll_interval_x}
                onChange={(e) =>
                  setNewBot({ ...newBot, poll_interval_x: parseInt(e.target.value, 10) || 60 })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>回看天数</div>
              <Input
                type="number"
                value={newBot.lookback_days}
                onChange={(e) =>
                  setNewBot({ ...newBot, lookback_days: parseInt(e.target.value, 10) || 3 })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>评论/小时</div>
              <Input
                type="number"
                value={newBot.comments_per_hour}
                onChange={(e) =>
                  setNewBot({
                    ...newBot,
                    comments_per_hour: parseInt(e.target.value, 10) || 10,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>最大连续失败</div>
              <Input
                type="number"
                value={newBot.max_consecutive_failures}
                onChange={(e) =>
                  setNewBot({
                    ...newBot,
                    max_consecutive_failures: parseInt(e.target.value, 10) || 5,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>LLM模型</div>
              <Input
                value={newBot.llm_model || ""}
                onChange={(e) => setNewBot({ ...newBot, llm_model: e.target.value })}
                placeholder="可选"
              />
            </div>
          </div>
        </div>
        {botModalError && (
          <div style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{botModalError}</div>
        )}
        {botModalLoading && (
          <div style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>处理中...</div>
        )}
      </Modal>

      <Modal
        open={showEditBotModal}
        title="编辑机器人"
        onClose={() => {
          setShowEditBotModal(false);
          setEditingBot(null);
          setEditBot({});
          setBotModalError("");
        }}
        onOk={handleUpdateBot}
        typewriter={false}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
              昵称
            </div>
            <Input
              value={editBot.nickname || ""}
              onChange={(e) => setEditBot({ ...editBot, nickname: e.target.value })}
              placeholder="机器人昵称"
            />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#794f27", marginBottom: 4 }}>
              人设
            </div>
            <textarea
              value={editBot.persona || ""}
              onChange={(e) => setEditBot({ ...editBot, persona: e.target.value })}
              placeholder="机器人人设描述"
              rows={4}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: 8,
                border: "1.5px solid #c4b89e",
                background: "rgb(247, 243, 223)",
                color: "#794f27",
                fontSize: 14,
                fontFamily: "inherit",
                resize: "vertical",
              }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>轮询间隔(秒)</div>
              <Input
                type="number"
                value={editBot.poll_interval_n}
                onChange={(e) =>
                  setEditBot({
                    ...editBot,
                    poll_interval_n: parseInt(e.target.value, 10) || undefined,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>随机偏移</div>
              <Input
                type="number"
                value={editBot.poll_interval_x}
                onChange={(e) =>
                  setEditBot({
                    ...editBot,
                    poll_interval_x: parseInt(e.target.value, 10) || undefined,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>回看天数</div>
              <Input
                type="number"
                value={editBot.lookback_days}
                onChange={(e) =>
                  setEditBot({
                    ...editBot,
                    lookback_days: parseInt(e.target.value, 10) || undefined,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>评论/小时</div>
              <Input
                type="number"
                value={editBot.comments_per_hour}
                onChange={(e) =>
                  setEditBot({
                    ...editBot,
                    comments_per_hour: parseInt(e.target.value, 10) || undefined,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>最大连续失败</div>
              <Input
                type="number"
                value={editBot.max_consecutive_failures}
                onChange={(e) =>
                  setEditBot({
                    ...editBot,
                    max_consecutive_failures: parseInt(e.target.value, 10) || undefined,
                  })
                }
              />
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#9f927d", marginBottom: 4 }}>LLM模型</div>
              <Input
                value={editBot.llm_model || ""}
                onChange={(e) => setEditBot({ ...editBot, llm_model: e.target.value })}
                placeholder="可选"
              />
            </div>
          </div>
        </div>
        {botModalError && (
          <div style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{botModalError}</div>
        )}
        {botModalLoading && (
          <div style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>处理中...</div>
        )}
      </Modal>

      <Modal
        open={showDeleteBotModal}
        title="确认停用机器人"
        onClose={() => {
          setShowDeleteBotModal(false);
          setDeletingBotId(null);
          setBotModalError("");
        }}
        onOk={handleDeleteBot}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要停用此机器人吗？</p>
        {botModalError && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{botModalError}</p>
        )}
        {botModalLoading && (
          <p style={{ color: "#9f927d", fontWeight: 500, marginTop: 8 }}>处理中...</p>
        )}
      </Modal>
    </div>
  );
}
