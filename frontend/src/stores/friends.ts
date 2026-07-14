import { create } from "zustand";
import { listFriendRequests } from "@/api/friends";
import { ApiError } from "@/api/client";

interface FriendsState {
  unreadCount: number;
  fetchUnread: () => Promise<void>;
  clearUnread: () => void;
}

export const useFriendsStore = create<FriendsState>((set) => ({
  unreadCount: 0,
  fetchUnread: async () => {
    try {
      const reqs = await listFriendRequests();
      set({ unreadCount: reqs.length });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      // 其它错误静默
    }
  },
  clearUnread: () => set({ unreadCount: 0 }),
}));
