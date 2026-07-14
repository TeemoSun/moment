import { useState, useRef, useEffect, type FormEvent, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Input, Card, Title, Modal, Tag, Tooltip } from "animal-island-ui";
import { useAuthStore } from "@/stores/auth";
import { updateMe, changePassword, uploadAvatar, deactivate } from "@/api/me";
import { getRsaPublicKey } from "@/api/auth";
import { encryptPassword } from "@/utils/rsa";
import { ApiError } from "@/api/client";
import { listInvites, createInvite, revokeInvite, renewInvite } from "@/api/invites";
import type { InviteOut } from "@/api/invites";
import { notify } from "@/utils/notify";
import { parseUTC } from "@/utils/time";

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, setUser, logout, clearUser, allowInsecureClipboard } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [signature, setSignature] = useState(user?.signature ?? "");
  const [profileSaving, setProfileSaving] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  const [avatarUploading, setAvatarUploading] = useState(false);

  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  const [invites, setInvites] = useState<InviteOut[]>([]);
  const [invitesLoading, setInvitesLoading] = useState(true);
  const [invitesError, setInvitesError] = useState("");
  const [durationDays, setDurationDays] = useState<number | null>(7);
  const [inviteActionLoading, setInviteActionLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setInvitesLoading(true);
      setInvitesError("");
      try {
        const data = await listInvites();
        setInvites(data);
      } catch (err) {
        setInvitesError(err instanceof ApiError ? err.message : "加载邀请码失败");
      } finally {
        setInvitesLoading(false);
      }
    };
    load();
  }, []);

  const handleCreateInvite = async () => {
    setInvitesError("");
    setInviteActionLoading(true);
    try {
      const newInvite = await createInvite({ duration_days: durationDays });
      setInvites((prev) => [newInvite, ...prev]);
      notify.success("邀请码已生成");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "生成邀请码失败");
    } finally {
      setInviteActionLoading(false);
    }
  };

  const handleRenewInvite = async () => {
    setInvitesError("");
    setInviteActionLoading(true);
    try {
      const renewed = await renewInvite({ duration_days: durationDays });
      setInvites((prev) => prev.map((inv) => (inv.id === renewed.id ? renewed : inv)));
      notify.success("已续期");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "续期失败");
    } finally {
      setInviteActionLoading(false);
    }
  };

  const handleRevokeInvite = async (id: number) => {
    setInvitesError("");
    try {
      await revokeInvite(id);
      setInvites((prev) =>
        prev.map((inv) => (inv.id === id ? { ...inv, status: "revoked" } : inv)),
      );
      notify.info("邀请码已失效");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "失效操作失败");
    }
  };

  const handleCopyLink = async (code: string) => {
    const link = `${window.location.origin}/register?invite=${code}`;
    const onCopied = () => {
      notify.success("邀请链接已复制");
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    };
    try {
      if (window.navigator.clipboard && window.isSecureContext) {
        await window.navigator.clipboard.writeText(link);
        onCopied();
        return;
      }
      if (!allowInsecureClipboard) {
        notify.error("复制失败");
        return;
      }
      const textarea = document.createElement("textarea");
      textarea.value = link;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      let ok = false;
      try {
        ok = document.execCommand("copy");
      } finally {
        document.body.removeChild(textarea);
      }
      if (ok) {
        onCopied();
      } else {
        notify.error("复制失败");
      }
    } catch {
      notify.error("复制失败");
    }
  };

  const formatExpiresAt = (expiresAt: string | null): string => {
    if (expiresAt === null) return "永久";
    const expTime = parseUTC(expiresAt).getTime();
    if (expTime < Date.now()) return "已过期";
    return parseUTC(expiresAt).toLocaleDateString();
  };

  const getStatusTagColor = (status: string): "app-teal" | "app-yellow" | "default" => {
    if (status === "active") return "app-teal";
    if (status === "expired") return "app-yellow";
    return "default";
  };

  const getStatusLabel = (status: string): string => {
    if (status === "active") return "有效";
    if (status === "used") return "已使用";
    if (status === "expired") return "已过期";
    if (status === "revoked") return "已失效";
    return status;
  };

  if (!user) return null;

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    try {
      const updated = await updateMe({
        nickname: nickname.trim() || undefined,
        signature: signature.trim(),
      });
      setUser(updated);
      notify.success("已保存");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordMsg("");

    if (!oldPassword || !newPassword) {
      setPasswordMsg("请填写旧密码和新密码");
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setPasswordMsg("两次新密码不一致");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordMsg("新密码至少 8 位");
      return;
    }

    setPasswordSaving(true);
    try {
      const { public_key } = await getRsaPublicKey();
      const encOld = encryptPassword(public_key, oldPassword);
      const encNew = encryptPassword(public_key, newPassword);
      await changePassword({ old_password: encOld, new_password: encNew });
      notify.success("密码已修改");
      setOldPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
      setPasswordMsg("");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleAvatarSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAvatarUploading(true);

    try {
      const res = await uploadAvatar(file);
      setUser({ ...user, avatar_url: `${res.avatar_url}?t=${Date.now()}` });
      notify.success("头像已更新");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "上传失败");
    } finally {
      setAvatarUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeactivate = async () => {
    setDeactivating(true);
    try {
      await deactivate();
      clearUser();
      navigate("/login", { replace: true });
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "注销失败");
    } finally {
      setDeactivating(false);
      setShowDeactivateModal(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div style={{ maxWidth: 560, margin: "40px auto", padding: "0 16px" }}>
      <Title color="app-teal">个人设置</Title>

      <Card style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 16 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={handleAvatarSelect}
          style={{ display: "none" }}
        />
        <Tooltip title="点击修改头像" placement="right" variant="island">
          <img
            src={user.avatar_url}
            alt="头像"
            onClick={() => fileInputRef.current?.click()}
            style={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              objectFit: "cover",
              border: "2.5px solid #c4b89e",
              cursor: "pointer",
              opacity: avatarUploading ? 0.5 : 1,
            }}
          />
        </Tooltip>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18, color: "#794f27" }}>{user.nickname}</div>
          <div style={{ color: "#9f927d", fontSize: 14 }}>{user.email}</div>
          {user.signature && (
            <div style={{ color: "#8a7b66", fontSize: 13, marginTop: 4 }}>{user.signature}</div>
          )}
        </div>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: "#794f27", marginBottom: 12 }}>
          修改资料
        </div>
        <form
          onSubmit={handleProfileSave}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontWeight: 600,
                fontSize: 14,
                color: "#794f27",
              }}
            >
              昵称
            </label>
            <Input
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="昵称"
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontWeight: 600,
                fontSize: 14,
                color: "#794f27",
              }}
            >
              签名
            </label>
            <Input
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              placeholder="一句话介绍自己"
            />
          </div>
          <Button type="primary" htmlType="submit" loading={profileSaving}>
            保存
          </Button>
        </form>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: "#794f27", marginBottom: 12 }}>
          修改密码
        </div>
        <form
          onSubmit={handlePasswordChange}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontWeight: 600,
                fontSize: 14,
                color: "#794f27",
              }}
            >
              旧密码
            </label>
            <Input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="当前密码"
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontWeight: 600,
                fontSize: 14,
                color: "#794f27",
              }}
            >
              新密码
            </label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="至少 8 位"
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                marginBottom: 4,
                fontWeight: 600,
                fontSize: 14,
                color: "#794f27",
              }}
            >
              确认新密码
            </label>
            <Input
              type="password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              placeholder="再次输入新密码"
            />
          </div>
          {passwordMsg && (
            <div
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: "#e05a5a",
              }}
            >
              {passwordMsg}
            </div>
          )}
          <Button type="primary" htmlType="submit" loading={passwordSaving}>
            修改密码
          </Button>
        </form>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: "#794f27", marginBottom: 12 }}>
          邀请码管理
        </div>
        {!user.can_invite && (
          <div
            style={{
              color: "#e05a5a",
              fontSize: 14,
              fontWeight: 500,
              marginBottom: 12,
            }}
          >
            你的邀请权限已被管理员关闭，无法生成邀请码
          </div>
        )}
        <div style={{ marginBottom: 12 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: "#794f27",
              marginBottom: 8,
            }}
          >
            有效期
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {[
              { label: "1 天", value: 1 },
              { label: "7 天", value: 7 },
              { label: "30 天", value: 30 },
              { label: "永久", value: null },
            ].map((opt) => (
              <Button
                key={opt.label}
                type={durationDays === opt.value ? "primary" : "default"}
                size="small"
                onClick={() => setDurationDays(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <Button
            type="primary"
            size="small"
            onClick={handleCreateInvite}
            loading={inviteActionLoading}
            disabled={!user.can_invite}
          >
            生成邀请码
          </Button>
          <Button
            type="default"
            size="small"
            onClick={handleRenewInvite}
            loading={inviteActionLoading}
            disabled={!user.can_invite}
          >
            续期
          </Button>
        </div>
        {invitesError && (
          <div
            style={{
              color: "#e05a5a",
              fontSize: 14,
              fontWeight: 500,
              marginBottom: 12,
            }}
          >
            {invitesError}
          </div>
        )}
        {invitesLoading ? (
          <div style={{ color: "#9f927d", fontSize: 14, fontWeight: 500 }}>加载中...</div>
        ) : invites.length === 0 ? (
          <div style={{ color: "#9f927d", fontSize: 14, fontWeight: 500 }}>暂无邀请码</div>
        ) : (
          <div>
            {invites.map((inv) => (
              <div
                key={inv.id}
                style={{
                  background: "rgb(247, 243, 223)",
                  borderRadius: 12,
                  padding: "10px 14px",
                  marginBottom: 8,
                  border: "1.5px solid #c4b89e",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontWeight: 700,
                      fontSize: 15,
                      color: "#794f27",
                    }}
                  >
                    {inv.code}
                  </span>
                  <Tag color={getStatusTagColor(inv.status)} size="small">
                    {getStatusLabel(inv.status)}
                  </Tag>
                  <span style={{ color: "#9f927d", fontSize: 13 }}>
                    {formatExpiresAt(inv.expires_at)}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginTop: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <Button type="default" size="small" onClick={() => handleCopyLink(inv.code)}>
                    {copiedCode === inv.code ? "已复制" : "复制链接"}
                  </Button>
                  {inv.status === "active" && (
                    <Button
                      type="default"
                      size="small"
                      danger
                      onClick={() => handleRevokeInvite(inv.id)}
                    >
                      失效
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Button type="default" onClick={() => navigate("/friends")}>
            好友列表
          </Button>
          <Button type="default" onClick={handleLogout}>
            登出
          </Button>
          <Button type="default" danger onClick={() => setShowDeactivateModal(true)}>
            注销账号
          </Button>
        </div>
      </Card>

      <Modal
        open={showDeactivateModal}
        title="确认注销"
        onClose={() => setShowDeactivateModal(false)}
        onOk={handleDeactivate}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>注销后账号将变为不可用状态，此操作不可撤销。确定要注销吗？</p>
        {deactivating && <p style={{ color: "#e05a5a", fontWeight: 600 }}>正在注销...</p>}
      </Modal>
    </div>
  );
}
