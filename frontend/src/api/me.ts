import { getJson, patchJson, postJson, upload } from "./client";

export interface MeOut {
  id: number;
  email: string;
  nickname: string;
  signature: string | null;
  avatar_url: string;
  role: string;
  status: string;
  can_invite: boolean;
  created_at: string;
}

export interface OtherUserOut {
  id: number;
  nickname: string;
  signature: string | null;
  avatar_url: string;
  is_deactivated: boolean;
  created_at: string;
  friendship_status: string;
  is_bot: boolean;
  persona_brief: string | null;
}

export interface MeUpdateIn {
  nickname?: string;
  signature?: string;
}

export interface PasswordChangeIn {
  old_password: string;
  new_password: string;
}

export interface AvatarOut {
  avatar_url: string;
}

export function getMe(): Promise<MeOut> {
  return getJson<MeOut>("/api/v1/me");
}

export function updateMe(data: MeUpdateIn): Promise<MeOut> {
  return patchJson<MeOut>("/api/v1/me", data);
}

export function changePassword(data: PasswordChangeIn): Promise<void> {
  return postJson<void>("/api/v1/me/password", data);
}

export function uploadAvatar(file: File): Promise<AvatarOut> {
  const formData = new FormData();
  formData.append("file", file);
  return upload<AvatarOut>("/api/v1/me/avatar", formData);
}

export function deactivate(): Promise<void> {
  return postJson<void>("/api/v1/me/deactivate");
}

export function getUser(userId: number): Promise<OtherUserOut> {
  return getJson<OtherUserOut>(`/api/v1/users/${userId}`);
}
