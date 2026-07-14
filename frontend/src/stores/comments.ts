import { create } from "zustand";
import type { CommentOut } from "@/api/comments";
import { getComments } from "@/api/comments";
import { ApiError } from "@/api/client";

interface CommentsState {
  items: CommentOut[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
  loading: boolean;
  loadingMore: boolean;
  error: string;
  fetchComments: (postId: number) => Promise<void>;
  loadMore: (postId: number) => Promise<void>;
  addComment: (comment: CommentOut) => void;
  removeComment: (id: number) => void;
  updateCommentLike: (id: number, liked: boolean, likeCount: number) => void;
  clear: () => void;
}

export const useCommentsStore = create<CommentsState>((set, get) => ({
  items: [],
  total: 0,
  page: 1,
  pageSize: 20,
  hasMore: false,
  loading: false,
  loadingMore: false,
  error: "",

  fetchComments: async (postId: number) => {
    set({ loading: true, error: "" });
    try {
      const res = await getComments(postId);
      set({
        items: res.items,
        total: res.total,
        page: res.page,
        pageSize: res.page_size,
        hasMore: res.has_more,
        loading: false,
      });
    } catch (err) {
      set({
        error: err instanceof ApiError ? err.message : "加载评论失败",
        loading: false,
      });
    }
  },

  loadMore: async (postId: number) => {
    const { hasMore, loadingMore, page, pageSize } = get();
    if (!hasMore || loadingMore) return;
    set({ loadingMore: true });
    try {
      const res = await getComments(postId, page + 1, pageSize);
      set((s) => ({
        items: [...s.items, ...res.items],
        total: res.total,
        page: res.page,
        hasMore: res.has_more,
        loadingMore: false,
      }));
    } catch (err) {
      set({
        error: err instanceof ApiError ? err.message : "加载更多评论失败",
        loadingMore: false,
      });
    }
  },

  addComment: (comment: CommentOut) => {
    set((s) => ({
      items: [...s.items, comment],
      total: s.total + 1,
    }));
  },

  removeComment: (id: number) => {
    set((s) => ({
      items: s.items.filter((c) => c.id !== id),
      total: Math.max(0, s.total - 1),
    }));
  },

  updateCommentLike: (id: number, liked: boolean, likeCount: number) => {
    set((s) => ({
      items: s.items.map((c) =>
        c.id === id ? { ...c, liked_by_me: liked, like_count: likeCount } : c,
      ),
    }));
  },

  clear: () => {
    set({
      items: [],
      total: 0,
      page: 1,
      pageSize: 20,
      hasMore: false,
      loading: false,
      loadingMore: false,
      error: "",
    });
  },
}));
