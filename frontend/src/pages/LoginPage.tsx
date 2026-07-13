import { useState, useEffect, useRef, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Input, Card, Title } from "animal-island-ui";
import { useAuthStore } from "@/stores/auth";
import { login, getRsaPublicKey } from "@/api/auth";
import { encryptPassword } from "@/utils/rsa";
import { ApiError } from "@/api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const { setUser } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lockCountdown, setLockCountdown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startCountdown = (seconds: number) => {
    setLockCountdown(seconds);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setLockCountdown((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("请填写邮箱和密码");
      return;
    }

    if (lockCountdown > 0) return;

    setSubmitting(true);
    try {
      const { public_key } = await getRsaPublicKey();
      const encrypted = encryptPassword(public_key, password);

      const { user } = await login({
        email: email.toLowerCase().trim(),
        password: encrypted,
      });

      setUser(user);
      navigate("/feed", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "ACCOUNT_LOCKED") {
          const retryAfter = (err.detail as { retry_after_seconds?: number }).retry_after_seconds;
          if (retryAfter) {
            startCountdown(retryAfter);
          }
          setError(`账号已锁定，请 ${retryAfter ?? "?"} 秒后重试`);
        } else {
          setError(err.message);
        }
      } else {
        setError("登录失败，请重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 480, margin: "60px auto", padding: "0 16px" }}>
      <Title color="app-yellow">登录</Title>
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
              密码
            </label>
            <Input
              type="password"
              placeholder="输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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

          <Button
            type="primary"
            htmlType="submit"
            block
            loading={submitting}
            disabled={lockCountdown > 0}
          >
            {lockCountdown > 0 ? `锁定中 (${lockCountdown}s)` : "登录"}
          </Button>
        </form>

        <div style={{ marginTop: 16, textAlign: "center", fontWeight: 500 }}>
          <span style={{ color: "#9f927d" }}>还没有账号？</span>{" "}
          <Link
            to="/register"
            style={{ color: "#19c8b9", fontWeight: 600, textDecoration: "none" }}
          >
            去注册
          </Link>
        </div>
      </Card>
    </div>
  );
}
