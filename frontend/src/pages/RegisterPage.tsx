import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Input, Card, Title } from "animal-island-ui";
import { useAuthStore } from "@/stores/auth";
import { register, getRsaPublicKey } from "@/api/auth";
import { encryptPassword } from "@/utils/rsa";
import { ApiError } from "@/api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setUser } = useAuthStore();
  const [email, setEmail] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [inviteCode, setInviteCode] = useState(searchParams.get("invite") ?? "");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !nickname || !password || !inviteCode) {
      setError("请填写所有字段");
      return;
    }

    if (password !== confirmPassword) {
      setError("两次密码不一致");
      return;
    }

    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }

    setSubmitting(true);
    try {
      const { public_key } = await getRsaPublicKey();
      const encrypted = encryptPassword(public_key, password);

      const { user } = await register({
        email: email.toLowerCase().trim(),
        nickname: nickname.trim(),
        password: encrypted,
        invite_code: inviteCode.trim(),
      });

      setUser(user);
      navigate("/settings", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("注册失败，请重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 480, margin: "60px auto", padding: "0 16px" }}>
      <Title color="app-green">注册</Title>
      <Card style={{ marginTop: 24 }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 600, color: "#794f27" }}>
              邮箱
            </label>
            <Input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 600, color: "#794f27" }}>
              昵称
            </label>
            <Input
              placeholder="你的昵称"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 600, color: "#794f27" }}>
              密码
            </label>
            <Input
              type="password"
              placeholder="至少 8 位"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 600, color: "#794f27" }}>
              确认密码
            </label>
            <Input
              type="password"
              placeholder="再次输入密码"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 600, color: "#794f27" }}>
              邀请码
            </label>
            <Input
              placeholder="输入邀请码"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
            />
          </div>

          {error && (
            <div
              style={{
                color: "#e05a5a",
                fontWeight: 500,
                fontSize: 14,
                padding: "8px 12px",
                background: "#fde8e8",
                borderRadius: 12,
              }}
            >
              {error}
            </div>
          )}

          <Button type="primary" htmlType="submit" block loading={submitting}>
            注册
          </Button>
        </form>

        <div style={{ marginTop: 16, textAlign: "center", fontWeight: 500 }}>
          <span style={{ color: "#9f927d" }}>已有账号？</span>{" "}
          <Link to="/login" style={{ color: "#19c8b9", fontWeight: 600, textDecoration: "none" }}>
            去登录
          </Link>
        </div>
      </Card>
    </div>
  );
}
