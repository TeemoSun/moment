import { getJson, patchJson, deleteJson, postJson, putJson } from "./client";

export interface StatsOut {
  user_count: number;
  post_count: number;
  comment_count: number;
  like_count: number;
  invite_count: number;
  used_invite_count: number;
}

export interface AdminAuthorOut {
  id: number;
  email: string;
  nickname: string;
  avatar_url: string;
  is_deactivated: boolean;
}

export interface AdminUserOut {
  id: number;
  email: string;
  nickname: string;
  role: string;
  status: string;
  can_invite: boolean;
  avatar_url: string;
  created_at: string;
  last_login_at: string | null;
}

export interface AdminUserListOut {
  items: AdminUserOut[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface AdminUserUpdateIn {
  status?: "active" | "disabled";
  can_invite?: boolean;
  restore?: boolean;
}

export interface AdminPostOut {
  id: number;
  content: string;
  visibility: string;
  deleted: boolean;
  author: AdminAuthorOut;
  like_count: number;
  comment_count: number;
  created_at: string;
  deleted_at: string | null;
}

export interface AdminPostListOut {
  items: AdminPostOut[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface AdminCommentOut {
  id: number;
  post_id: number;
  content: string | null;
  image_thumb_url: string | null;
  deleted: boolean;
  author: AdminAuthorOut;
  like_count: number;
  created_at: string;
  deleted_at: string | null;
}

export interface AdminCommentListOut {
  items: AdminCommentOut[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface AdminInviteOut {
  id: number;
  code: string;
  status: string;
  expires_at: string | null;
  created_at: string;
  used_by_id: number | null;
  creator: AdminAuthorOut;
}

export interface AdminInviteListOut {
  items: AdminInviteOut[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export function getStats(): Promise<StatsOut> {
  return getJson<StatsOut>("/api/v1/admin/stats");
}

export function listUsers(search?: string, page = 1, pageSize = 20): Promise<AdminUserListOut> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return getJson<AdminUserListOut>(`/api/v1/admin/users?${params.toString()}`);
}

export function updateUser(userId: number, data: AdminUserUpdateIn): Promise<AdminUserOut> {
  return patchJson<AdminUserOut>(`/api/v1/admin/users/${userId}`, data);
}

export function listPosts(
  userId?: number,
  visibility?: string,
  page = 1,
  pageSize = 20,
): Promise<AdminPostListOut> {
  const params = new URLSearchParams();
  if (userId) params.set("user_id", String(userId));
  if (visibility) params.set("visibility", visibility);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return getJson<AdminPostListOut>(`/api/v1/admin/posts?${params.toString()}`);
}

export function deletePost(postId: number): Promise<void> {
  return deleteJson<void>(`/api/v1/admin/posts/${postId}`);
}

export function listComments(page = 1, pageSize = 20): Promise<AdminCommentListOut> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return getJson<AdminCommentListOut>(`/api/v1/admin/comments?${params.toString()}`);
}

export function deleteComment(commentId: number): Promise<void> {
  return deleteJson<void>(`/api/v1/admin/comments/${commentId}`);
}

export function listInvites(page = 1, pageSize = 20): Promise<AdminInviteListOut> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return getJson<AdminInviteListOut>(`/api/v1/admin/invites?${params.toString()}`);
}

export function revokeInvite(inviteId: number): Promise<{ message: string }> {
  return postJson<{ message: string }>(`/api/v1/admin/invites/${inviteId}/revoke`);
}

export interface LLMConfigOut {
  base_url: string;
  model: string;
  timeout: number;
  max_tokens: number;
  has_api_key: boolean;
}

export interface LLMConfigUpdateIn {
  base_url?: string;
  api_key?: string;
  model?: string;
  timeout?: number;
  max_tokens?: number;
}

export interface LLMConfigTestIn {
  base_url?: string;
  api_key?: string;
  model?: string;
  timeout?: number;
  max_tokens?: number;
}

export interface LLMTestOut {
  success: boolean;
  message: string;
}

export function getLLMConfig(): Promise<LLMConfigOut> {
  return getJson<LLMConfigOut>("/api/v1/admin/llm-config");
}

export function updateLLMConfig(data: LLMConfigUpdateIn): Promise<LLMConfigOut> {
  return putJson<LLMConfigOut>("/api/v1/admin/llm-config", data);
}

export function testLLMConfig(data: LLMConfigTestIn): Promise<LLMTestOut> {
  return postJson<LLMTestOut>("/api/v1/admin/llm-config/test", data);
}
