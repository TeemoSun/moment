import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button, Title, Tag } from "animal-island-ui";
import { useAuthStore } from "@/stores/auth";
import { useFriendsStore } from "@/stores/friends";
import { notify } from "@/utils/notify";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import type { ReactNode } from "react";

interface NavItem {
  label: string;
  path?: string;
  onClick?: () => void;
  badge?: number;
}

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { unreadCount, fetchUnread } = useFriendsStore();
  const isMobile = useMediaQuery("(max-width: 639px)");

  useEffect(() => {
    if (user) fetchUnread();
  }, [user, fetchUnread]);

  const handleLogout = async () => {
    await logout();
    notify.info("已登出");
    navigate("/login", { replace: true });
  };

  const isActive = (path: string) => location.pathname === path;

  const navItems: NavItem[] = [
    { label: "动态", path: "/feed" },
    { label: "发动态", path: "/post/create" },
    { label: "好友", path: "/friends", badge: unreadCount > 0 ? unreadCount : undefined },
    { label: "设置", path: "/settings" },
    ...(user?.role === "admin" ? [{ label: "管理后台", path: "/admin" }] : []),
  ];

  return (
    <>
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          background: "#f8f8f0",
          borderBottom: "2px solid #e8dcc8",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: isMobile ? "8px 12px" : "10px 20px",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <span
          onClick={() => navigate("/feed")}
          style={{ cursor: "pointer", flexShrink: 0 }}
        >
          <Title size="small" color="app-teal">
            Moments
          </Title>
        </span>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: isMobile ? 4 : 8,
          }}
        >
          {navItems.map((item) => {
            const active = item.path ? isActive(item.path) : false;
            return (
              <Button
                key={item.label}
                type={active ? "primary" : "default"}
                size="small"
                onClick={() => item.path && navigate(item.path)}
                style={isMobile ? { fontSize: 12, padding: "0 10px" } : undefined}
              >
                <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                  {item.label}
                  {item.badge !== undefined && (
                    <Tag color="app-red" size="small" style={{ marginLeft: 2 }}>
                      {item.badge}
                    </Tag>
                  )}
                </span>
              </Button>
            );
          })}
          <Button
            type="default"
            size="small"
            onClick={handleLogout}
            style={isMobile ? { fontSize: 12, padding: "0 10px" } : undefined}
          >
            登出
          </Button>
        </div>
      </nav>
      <main>{children}</main>
    </>
  );
}