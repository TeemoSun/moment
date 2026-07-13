import { getJson, postJson } from "./client";
import type { MeOut } from "./me";

export interface InitializedOut {
  initialized: boolean;
}

export interface InitIn {
  email: string;
  nickname: string;
  password: string;
}

export interface TokenOut {
  user: MeOut;
}

export function getInitialized(): Promise<InitializedOut> {
  return getJson<InitializedOut>("/api/v1/system/initialized");
}

export function initSystem(data: InitIn): Promise<TokenOut> {
  return postJson<TokenOut>("/api/v1/system/init", data, { withCsrf: false });
}
