import { create } from "zustand";
import type { MeOut } from "@/api/me";
import { getMe as fetchMeApi } from "@/api/me";
import { getInitialized } from "@/api/system";
import { logout as logoutApi } from "@/api/auth";
import { setUnauthorizedHandler } from "@/api/client";

interface AuthState {
  user: MeOut | null;
  loading: boolean;
  initialized: boolean | null;
  bootstrapped: boolean;
  fetchInitialized: () => Promise<void>;
  fetchMe: () => Promise<void>;
  setUser: (u: MeOut | null) => void;
  clearUser: () => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: null,
  bootstrapped: false,

  fetchInitialized: async () => {
    try {
      const res = await getInitialized();
      set({ initialized: res.initialized });
    } catch {
      set({ initialized: false });
    }
  },

  fetchMe: async () => {
    set({ loading: true });
    try {
      const user = await fetchMeApi();
      set({ user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  setUser: (u) => {
    set({ user: u });
  },

  clearUser: () => {
    set({ user: null });
  },

  logout: async () => {
    try {
      await logoutApi();
    } catch {
      // ignore
    }
    set({ user: null });
  },
}));

setUnauthorizedHandler(() => {
  useAuthStore.getState().setUser(null);
});
