import { getJson, postJson } from "./client";

export interface InviteOut {
  id: number;
  code: string;
  status: string;
  expires_at: string | null;
  created_at: string;
  used_by_id: number | null;
}

export interface InviteCreateIn {
  duration_days: number | null;
}

export interface InviteActionOut {
  message: string;
}

export function createInvite(data: InviteCreateIn): Promise<InviteOut> {
  return postJson<InviteOut>("/api/v1/invites", data);
}

export function listInvites(): Promise<InviteOut[]> {
  return getJson<InviteOut[]>("/api/v1/invites");
}

export function revokeInvite(id: number): Promise<InviteActionOut> {
  return postJson<InviteActionOut>(`/api/v1/invites/${id}/revoke`);
}

export function renewInvite(data: InviteCreateIn): Promise<InviteOut> {
  return postJson<InviteOut>("/api/v1/invites/renew", data);
}
