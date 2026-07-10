export interface User {
  id: string
  username: string
  display_name: string
  bio: string
  avatar_url: string | null
  created_at: string
}

export interface UserBrief {
  id: string
  username: string
  display_name: string
  avatar_url: string | null
}

export interface Media {
  id: string
  media_type: 'image' | 'video'
  mime_type: string
  file_format: string
  size_bytes: number
  width: number | null
  height: number | null
  duration: number | null
  original_filename: string
  small_url: string | null
  medium_url: string | null
  original_url: string | null
}

export interface Post {
  id: string
  user: UserBrief
  content: string
  visibility: 'public' | 'friends'
  media: Media[]
  comment_count: number
  like_count: number
  liked: boolean
  created_at: string
  updated_at?: string
  deleted_at?: string | null
}

export interface Comment {
  id: string
  post_id: string
  user: UserBrief
  parent_id: string | null
  root_id: string
  reply_to_user: UserBrief | null
  depth: number
  content: string
  created_at: string
  deleted: boolean
  reply_count: number
  like_count: number
  liked: boolean
}

export interface CommentTree {
  root: Comment
  replies: Comment[]
  total_replies: number
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface Friend {
  id: string
  user: UserBrief
  status: string
  accepted_at: string | null
}

export interface FriendRequest {
  id: string
  requester: UserBrief
  addressee_id: string
  status: string
  created_at: string
}

export interface TokenOut {
  access_token: string
  token_type: string
  user: User
}

export interface LoginIn {
  username: string
  password: string
}

export interface RegisterIn {
  invite_code: string
  username: string
  email: string
  password: string
}

export interface InviteCode {
  id: string
  code: string
  max_uses: number
  used_count: number
  expires_at: string | null
  created_at: string
}