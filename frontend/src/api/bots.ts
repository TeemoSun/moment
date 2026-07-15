import { getJson, postJson, deleteJson, patchJson, upload } from "./client";

export interface BotPublicOut {
  id: number;
  user_id: number;
  nickname: string;
  avatar_url: string;
  persona_brief: string;
  is_friend: boolean;
}

export interface BotAdminOut {
  id: number;
  user_id: number;
  nickname: string;
  email: string;
  avatar_url: string;
  persona: string;
  poll_interval_n: number;
  poll_interval_x: number;
  lookback_days: number;
  comments_per_hour: number;
  max_consecutive_failures: number;
  llm_model: string | null;
  enabled: boolean;
  auto_paused: boolean;
  consecutive_failures: number;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface BotCreateIn {
  nickname: string;
  persona: string;
  poll_interval_n?: number;
  poll_interval_x?: number;
  lookback_days?: number;
  comments_per_hour?: number;
  max_consecutive_failures?: number;
  llm_model?: string | null;
}

export interface BotUpdateIn {
  nickname?: string;
  persona?: string;
  poll_interval_n?: number;
  poll_interval_x?: number;
  lookback_days?: number;
  comments_per_hour?: number;
  max_consecutive_failures?: number;
  llm_model?: string | null;
  enabled?: boolean;
  restore?: boolean;
}

export function listBotsPublic(): Promise<BotPublicOut[]> {
  return getJson<BotPublicOut[]>("/api/v1/friends/bots");
}

export function addBotFriend(botUserId: number): Promise<{ message: string }> {
  return postJson<{ message: string }>(`/api/v1/friends/bots/${botUserId}`);
}

export function removeBotFriend(botUserId: number): Promise<void> {
  return deleteJson<void>(`/api/v1/friends/${botUserId}`);
}

export function listBotsAdmin(): Promise<BotAdminOut[]> {
  return getJson<BotAdminOut[]>("/api/v1/admin/bots");
}

export function createBot(data: BotCreateIn): Promise<BotAdminOut> {
  return postJson<BotAdminOut>("/api/v1/admin/bots", data);
}

export function updateBot(botId: number, data: BotUpdateIn): Promise<BotAdminOut> {
  return patchJson<BotAdminOut>(`/api/v1/admin/bots/${botId}`, data);
}

export function deleteBot(botId: number): Promise<{ message: string }> {
  return deleteJson<{ message: string }>(`/api/v1/admin/bots/${botId}`);
}

export function uploadBotAvatar(botId: number, file: File): Promise<{ message: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return upload<{ message: string }>(`/api/v1/admin/bots/${botId}/avatar`, formData);
}

export function triggerBotNow(botId: number): Promise<{ message: string }> {
  return postJson<{ message: string }>(`/api/v1/admin/bots/${botId}/trigger`);
}
