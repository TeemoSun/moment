import { getJson, postJson, deleteJson } from "./client";
import type { CommentOut } from "./comments";

export interface LikeAuthorOut {
  id: number;
  nickname: string;
  avatar_url: string;
  is_deactivated: boolean;
}

export interface AuthorOut {
  id: number;
  nickname: string;
  avatar_url: string;
  is_deactivated: boolean;
}

export interface MediaBriefOut {
  id: number;
  kind: string;
  sort_order: number;
  thumb_url: string | null;
  large_url: string | null;
  original_url: string | null;
}

export interface PostOut {
  id: number;
  content: string;
  visibility: string;
  author: AuthorOut;
  media: MediaBriefOut[];
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
  is_owner: boolean;
  created_at: string;
  updated_at: string;
  preview_comments: CommentOut[];
  like_authors: LikeAuthorOut[];
}

export interface FeedOut {
  items: PostOut[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface PostCreateIn {
  content: string;
  media_ids: number[];
  visibility: "public" | "friends";
}

export function getFeed(cursor?: string, limit = 20): Promise<FeedOut> {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  params.set("limit", String(limit));
  return getJson<FeedOut>(`/api/v1/feed?${params.toString()}`);
}

export function getPost(id: number): Promise<PostOut> {
  return getJson<PostOut>(`/api/v1/posts/${id}`);
}

export function createPost(data: PostCreateIn): Promise<PostOut> {
  return postJson<PostOut>("/api/v1/posts", data);
}

export function deletePost(id: number): Promise<void> {
  return deleteJson<void>(`/api/v1/posts/${id}`);
}

export function getUserPosts(userId: number, cursor?: string, limit = 20): Promise<FeedOut> {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  params.set("limit", String(limit));
  return getJson<FeedOut>(`/api/v1/users/${userId}/posts?${params.toString()}`);
}
