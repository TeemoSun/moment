import { getJson, postJson, deleteJson, upload } from "./client";

export interface CommentAuthorOut {
  id: number;
  nickname: string;
  avatar_url: string;
  is_deactivated: boolean;
}

export interface ReplyToOut {
  id: number;
  nickname: string;
  is_deactivated: boolean;
}

export interface CommentOut {
  id: number;
  post_id: number;
  author: CommentAuthorOut;
  parent_comment_id: number | null;
  reply_to: ReplyToOut | null;
  content: string | null;
  image_thumb_url: string | null;
  image_large_url: string | null;
  like_count: number;
  liked_by_me: boolean;
  is_owner: boolean;
  can_delete: boolean;
  created_at: string;
}

export interface CommentListOut {
  items: CommentOut[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface CommentCreateIn {
  content?: string | null;
  media_id?: number | null;
  parent_comment_id?: number | null;
  reply_to_user_id?: number | null;
}

export interface LikeCountOut {
  target_type: string;
  target_id: number;
  like_count: number;
  liked_by_me: boolean;
}

export interface CommentMediaOut {
  media_id: number;
  status: string;
}

export function getComments(
  postId: number,
  page = 1,
  pageSize = 20,
): Promise<CommentListOut> {
  return getJson<CommentListOut>(
    `/api/v1/posts/${postId}/comments?page=${page}&page_size=${pageSize}`,
  );
}

export function createComment(
  postId: number,
  data: CommentCreateIn,
): Promise<CommentOut> {
  return postJson<CommentOut>(`/api/v1/posts/${postId}/comments`, data);
}

export function deleteComment(commentId: number): Promise<void> {
  return deleteJson<void>(`/api/v1/comments/${commentId}`);
}

export function likePost(postId: number): Promise<LikeCountOut> {
  return postJson<LikeCountOut>(`/api/v1/posts/${postId}/likes`);
}

export function likeComment(commentId: number): Promise<LikeCountOut> {
  return postJson<LikeCountOut>(`/api/v1/comments/${commentId}/likes`);
}

export function uploadCommentImage(file: File): Promise<CommentMediaOut> {
  const formData = new FormData();
  formData.append("file", file);
  return upload<CommentMediaOut>("/api/v1/comments/media", formData);
}
