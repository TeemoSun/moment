import { useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import RequireAuth from "@/components/RequireAuth";
import InitPage from "@/pages/InitPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import SettingsPage from "@/pages/SettingsPage";
import FeedPage from "@/pages/FeedPage";
import PostCreatePage from "@/pages/PostCreatePage";
import UserPage from "@/pages/UserPage";
import PostDetailPage from "@/pages/PostDetailPage";
import FriendsPage from "@/pages/FriendsPage";

function AppRoutes() {
  const { initialized, user, fetchInitialized, fetchMe } = useAuthStore();
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
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (initialized === null) {
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
            <FeedPage />
          </RequireAuth>
        }
      />
      <Route
        path="/post/create"
        element={
          <RequireAuth>
            <PostCreatePage />
          </RequireAuth>
        }
      />
      <Route
        path="/users/:userId"
        element={
          <RequireAuth>
            <UserPage />
          </RequireAuth>
        }
      />
      <Route
        path="/posts/:postId"
        element={
          <RequireAuth>
            <PostDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAuth>
            <SettingsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/friends"
        element={
          <RequireAuth>
            <FriendsPage />
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
