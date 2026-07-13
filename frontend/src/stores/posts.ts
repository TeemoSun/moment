import { create } from "zustand";
import type { PostOut } from "@/api/posts";
import { getFeed } from "@/api/posts";
import { ApiError } from "@/api/client";

interface PostsState {
  items: PostOut[];
  nextCursor: string | null;
  hasMore: boolean;
  loading: boolean;
  loadingMore: boolean;
  error: string;
  fetchFeed: () => Promise<void>;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  removePost: (id: number) => void;
  prependPost: (post: PostOut) => void;
  clear: () => void;
}

export const usePostsStore = create<PostsState>((set, get) => ({
  items: [],
  nextCursor: null,
  hasMore: false,
  loading: false,
  loadingMore: false,
  error: "",

  fetchFeed: async () => {
    set({ loading: true, error: "" });
    try {
      const res = await getFeed();
      set({
        items: res.items,
        nextCursor: res.next_cursor,
        hasMore: res.has_more,
        loading: false,
      });
    } catch (err) {
      set({
        error: err instanceof ApiError ? err.message : "加载失败",
        loading: false,
      });
    }
  },

  loadMore: async () => {
    const { nextCursor, hasMore, loadingMore } = get();
    if (!hasMore || loadingMore || !nextCursor) return;
    set({ loadingMore: true });
    try {
      const res = await getFeed(nextCursor);
      set((s) => ({
        items: [...s.items, ...res.items],
        nextCursor: res.next_cursor,
        hasMore: res.has_more,
        loadingMore: false,
      }));
    } catch (err) {
      set({
        error: err instanceof ApiError ? err.message : "加载更多失败",
        loadingMore: false,
      });
    }
  },

  refresh: async () => {
    set({ items: [], nextCursor: null, hasMore: false, error: "" });
    await get().fetchFeed();
  },

  removePost: (id: number) => {
    set((s) => ({ items: s.items.filter((p) => p.id !== id) }));
  },

  prependPost: (post: PostOut) => {
    set((s) => ({ items: [post, ...s.items] }));
  },

  clear: () => {
    set({ items: [], nextCursor: null, hasMore: false, error: "", loading: false, loadingMore: false });
  },
}));
