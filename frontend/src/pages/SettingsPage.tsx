import { useState, useRef, type FormEvent, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Input, Card, Title, Modal } from "animal-island-ui";
import { useAuthStore } from "@/stores/auth";
import { updateMe, changePassword, uploadAvatar, deactivate } from "@/api/me";
import { getRsaPublicKey } from "@/api/auth";
import { encryptPassword } from "@/utils/rsa";
import { ApiError } from "@/api/client";

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, setUser, logout, clearUser } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [signature, setSignature] = useState(user?.signature ?? "");
  const [profileMsg, setProfileMsg] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarMsg, setAvatarMsg] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  if (!user) return null;

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setProfileMsg("");
    setProfileSaving(true);
    try {
      const updated = await updateMe({
        nickname: nickname.trim() || undefined,
        signature: signature.trim() || undefined,
      });
      setUser(updated);
      setProfileMsg("已保存");
    } catch (err) {
      setProfileMsg(err instanceof ApiError ? err.message : "保存失败");
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
      setPasswordMsg("密码已修改");
      setOldPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
    } catch (err) {
      setPasswordMsg(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleAvatarSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    setAvatarMsg("");
    setAvatarUploading(true);

    try {
      const res = await uploadAvatar(file);
      setUser({ ...user, avatar_url: res.avatar_url });
      setAvatarMsg("头像已更新");
    } catch (err) {
      setAvatarMsg(err instanceof ApiError ? err.message : "上传失败");
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
      setPasswordMsg(err instanceof ApiError ? err.message : "注销失败");
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
        <img
          src={user.avatar_url}
          alt="avatar"
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
          <div style={{ color: "#9f927d", fontSize: 14 }}>{user.email}</div>
          {user.signature && (
            <div style={{ color: "#8a7b66", fontSize: 13, marginTop: 4 }}>{user.signature}</div>
          )}
        </div>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: "#794f27", marginBottom: 12 }}>
          头像
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {previewUrl && (
            <img
              src={previewUrl}
              alt="preview"
              style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                objectFit: "cover",
                border: "2px solid #c4b89e",
              }}
            />
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleAvatarSelect}
            style={{ display: "none" }}
          />
          <Button
            type="default"
            size="small"
            onClick={() => fileInputRef.current?.click()}
            loading={avatarUploading}
          >
            选择图片
          </Button>
        </div>
        {avatarMsg && (
          <div
            style={{
              marginTop: 8,
              fontSize: 14,
              fontWeight: 500,
              color: avatarMsg.includes("失败") ? "#e05a5a" : "#6fba2c",
            }}
          >
            {avatarMsg}
          </div>
        )}
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
          {profileMsg && (
            <div
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: profileMsg === "已保存" ? "#6fba2c" : "#e05a5a",
              }}
            >
              {profileMsg}
            </div>
          )}
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
                color: passwordMsg === "密码已修改" ? "#6fba2c" : "#e05a5a",
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
