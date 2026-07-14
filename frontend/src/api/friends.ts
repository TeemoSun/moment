import { getJson, postJson, deleteJson } from "./client";

export interface FriendUserBrief {
  id: number;
  nickname: string;
  avatar_url: string;
  is_deactivated: boolean;
}

export interface FriendRequestOut {
  id: number;
  requester: FriendUserBrief;
  created_at: string;
}

export interface FriendOut {
  id: number;
  user: FriendUserBrief;
  since: string;
  requester_id: number;
}

export interface FriendRequestActionOut {
  message: string;
}

export interface FriendRequestIn {
  email: string;
}

export function requestFriend(data: FriendRequestIn): Promise<FriendRequestActionOut> {
  return postJson<FriendRequestActionOut>("/api/v1/friends/request", data);
}

export function listFriendRequests(): Promise<FriendRequestOut[]> {
  return getJson<FriendRequestOut[]>("/api/v1/friends/requests");
}

export function acceptFriendRequest(requestId: number): Promise<FriendRequestActionOut> {
  return postJson<FriendRequestActionOut>(`/api/v1/friends/requests/${requestId}/accept`);
}

export function rejectFriendRequest(requestId: number): Promise<FriendRequestActionOut> {
  return postJson<FriendRequestActionOut>(`/api/v1/friends/requests/${requestId}/reject`);
}

export function listFriends(): Promise<FriendOut[]> {
  return getJson<FriendOut[]>("/api/v1/friends");
}

export function removeFriend(userId: number): Promise<void> {
  return deleteJson<void>(`/api/v1/friends/${userId}`);
}
