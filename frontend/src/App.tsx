import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuthStore } from './stores/auth'
import { getAccessToken, refreshSession, setRestoringDone } from './api/client'
import { AppLayout } from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import FeedPage from './pages/FeedPage'
import PostDetailPage from './pages/PostDetailPage'
import ProfilePage from './pages/ProfilePage'
import FriendsPage from './pages/FriendsPage'
import ComposePage from './pages/ComposePage'
import SettingsPage from './pages/SettingsPage'

function ProtectedRoute({ children, restoring }: { children: React.ReactNode; restoring: boolean }) {
  const user = useAuthStore((s) => s.user)
  const token = getAccessToken()
  if (restoring) return null
  if (!user || !token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const location = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)
  const logout = useAuthStore((s) => s.logout)
  const [restoring, setRestoring] = useState(true)

  useEffect(() => {
    const existingToken = getAccessToken()
    if (existingToken && useAuthStore.getState().user) {
      setRestoringDone()
      setRestoring(false)
      return
    }
    refreshSession()
      .then((result) => {
        if (!result) {
          logout()
          return
        }
        setAuth(result.user, result.token)
      })
      .catch(() => logout())
      .finally(() => {
        setRestoringDone()
        setRestoring(false)
      })
  }, [setAuth, logout])

  if (restoring) return null

  if ((location.pathname === '/login' || location.pathname === '/register') && useAuthStore.getState().user) {
    return <Navigate to="/" replace />
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute restoring={restoring}><AppLayout /></ProtectedRoute>}>
        <Route path="/" element={<FeedPage />} />
        <Route path="/post/:id" element={<PostDetailPage />} />
        <Route path="/u/:username" element={<ProfilePage />} />
        <Route path="/friends" element={<FriendsPage />} />
        <Route path="/compose" element={<ComposePage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}