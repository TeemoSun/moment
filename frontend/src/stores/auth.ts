import { create } from 'zustand'
import type { User } from '@/api/types'
import { setAccessToken } from '@/api/client'

interface AuthState {
  user: User | null
  accessToken: string | null
  setAuth: (user: User, token: string) => void
  updateUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  setAuth: (user, token) => {
    setAccessToken(token)
    set({ user, accessToken: token })
  },
  updateUser: (user) => set({ user }),
  logout: () => {
    setAccessToken(null)
    set({ user: null, accessToken: null })
  },
}))