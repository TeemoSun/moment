import { useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import RequireAuth from "@/components/RequireAuth";
import Layout from "@/components/Layout";
import InitPage from "@/pages/InitPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import SettingsPage from "@/pages/SettingsPage";
import FeedPage from "@/pages/FeedPage";
import PostCreatePage from "@/pages/PostCreatePage";
import UserPage from "@/pages/UserPage";
import PostDetailPage from "@/pages/PostDetailPage";
import FriendsPage from "@/pages/FriendsPage";
import AdminPage from "@/pages/AdminPage";

function AppRoutes() {
  const { initialized, user, bootstrapped, fetchInitialized, fetchMe } = useAuthStore();
  const location = useLocation();
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const init = async () => {
      await fetchInitialized();
      const state = useAuthStore.getState();
      if (state.initialized && location.pathname !== "/init") {
        await fetchMe();
      }
      useAuthStore.setState({ bootstrapped: true });
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (initialized === null || !bootstrapped) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          fontWeight: 600,
          color: "#9f927d",
          fontSize: 18,
        }}
      >
        加载中...
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          !initialized ? (
            <Navigate to="/init" replace />
          ) : !user ? (
            <Navigate to="/login" replace />
          ) : (
            <Navigate to="/feed" replace />
          )
        }
      />
      <Route path="/init" element={<InitPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/feed"
        element={
          <RequireAuth>
            <Layout>
              <FeedPage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/post/create"
        element={
          <RequireAuth>
            <Layout>
              <PostCreatePage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/users/:userId"
        element={
          <RequireAuth>
            <Layout>
              <UserPage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/posts/:postId"
        element={
          <RequireAuth>
            <Layout>
              <PostDetailPage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAuth>
            <Layout>
              <SettingsPage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/friends"
        element={
          <RequireAuth>
            <Layout>
              <FriendsPage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth role="admin">
            <Layout>
              <AdminPage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
