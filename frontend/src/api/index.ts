import api from './client'
import type { Comment, CommentTree, Friend, FriendRequest, InviteCode, LoginIn, Paginated, Post, RegisterIn, TokenOut, User, UserBrief } from './types'

export const authApi = {
  register: (data: RegisterIn) => api.post<TokenOut>('/api/auth/register', data).then((r) => r.data),
  login: (data: LoginIn) => api.post<TokenOut>('/api/auth/login', data).then((r) => r.data),
  logout: () => api.post('/api/auth/logout'),
}

export const userApi = {
  me: () => api.get<User>('/api/users/me').then((r) => r.data),
  updateMe: (data: { display_name?: string; bio?: string }) =>
    api.patch<User>('/api/users/me', data).then((r) => r.data),
  uploadAvatar: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<User>('/api/users/me/avatar', fd).then((r) => r.data)
  },
  get: (id: string) => api.get<User>(`/api/users/${id}`).then((r) => r.data),
  getByUsername: (username: string) => api.get<User>(`/api/users/by-username/${username}`).then((r) => r.data),
}

export const postApi = {
  create: (data: { content: string; media_ids: string[]; visibility: string }) =>
    api.post<Post>('/api/posts', data).then((r) => r.data),
  feed: (page = 1, pageSize = 20) =>
    api.get<Paginated<Post>>('/api/posts/feed', { params: { page, page_size: pageSize } }).then((r) => r.data),
  myPosts: (page = 1, pageSize = 20) =>
    api.get<Paginated<Post>>('/api/posts/me', { params: { page, page_size: pageSize } }).then((r) => r.data),
  get: (id: string) => api.get<Post>(`/api/posts/${id}`).then((r) => r.data),
  update: (id: string, data: { content?: string; visibility?: string }) =>
    api.patch<Post>(`/api/posts/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/api/posts/${id}`).then((r) => r.data),
  like: (id: string) => api.post(`/api/posts/${id}/likes`).then((r) => r.data),
  unlike: (id: string) => api.delete(`/api/posts/${id}/likes`).then((r) => r.data),
}

export const commentApi = {
  create: (postId: string, data: { content: string; parent_id?: string | null; reply_to_user_id?: string | null }) =>
    api.post(`/api/posts/${postId}/comments`, data).then((r) => r.data),
  reply: (commentId: string, data: { content: string; reply_to_user_id?: string | null }) =>
    api.post(`/api/comments/${commentId}/replies`, data).then((r) => r.data),
  list: (postId: string, page = 1, pageSize = 20) =>
    api.get<Paginated<CommentTree>>(`/api/posts/${postId}/comments`, { params: { page, page_size: pageSize } }).then((r) => r.data),
  listReplies: (commentId: string, page = 1, pageSize = 50) =>
    api.get<Paginated<Comment>>(`/api/comments/${commentId}/replies`, { params: { page, page_size: pageSize } }).then((r) => r.data),
  delete: (id: string) => api.delete(`/api/comments/${id}`).then((r) => r.data),
  like: (id: string) => api.post(`/api/comments/${id}/likes`).then((r) => r.data),
  unlike: (id: string) => api.delete(`/api/comments/${id}/likes`).then((r) => r.data),
}

export const friendApi = {
  requests: () => api.get<FriendRequest[]>(`/api/friends/requests`).then((r) => r.data),
  send: (username: string) => api.post(`/api/friends/requests/${username}`).then((r) => r.data),
  accept: (id: string) => api.post(`/api/friends/requests/${id}/accept`).then((r) => r.data),
  reject: (id: string) => api.post(`/api/friends/requests/${id}/reject`).then((r) => r.data),
  list: () => api.get<Friend[]>(`/api/friends`).then((r) => r.data),
  remove: (id: string) => api.delete(`/api/friends/${id}`).then((r) => r.data),
}

export const mediaApi = {
  upload: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/media', fd).then((r) => r.data)
  },
}

export const adminApi = {
  createInvite: (maxUses = 1, expiresDays?: number) =>
    api.post<InviteCode>('/api/admin/invite-codes', null, { params: { max_uses: maxUses, expires_days: expiresDays } }).then((r) => r.data),
  listInvites: () => api.get<InviteCode[]>('/api/admin/invite-codes').then((r) => r.data),
  listUsers: (page = 1, pageSize = 50) =>
    api.get<Paginated<UserBrief>>('/api/admin/users', { params: { page, page_size: pageSize } }).then((r) => r.data),
}