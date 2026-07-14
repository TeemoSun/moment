import { getJson, postJson } from "./client";
import type { MeOut } from "./me";

export interface RSAKeyOut {
  public_key: string;
}

export interface RegisterIn {
  email: string;
  nickname: string;
  password: string;
  invite_code: string;
}

export interface LoginIn {
  email: string;
  password: string;
}

export interface TokenOut {
  user: MeOut;
}

export function getRsaPublicKey(): Promise<RSAKeyOut> {
  return getJson<RSAKeyOut>("/api/v1/auth/rsa-public-key");
}

export function register(data: RegisterIn): Promise<TokenOut> {
  return postJson<TokenOut>("/api/v1/auth/register", data, { withCsrf: false });
}

export function login(data: LoginIn): Promise<TokenOut> {
  return postJson<TokenOut>("/api/v1/auth/login", data, { withCsrf: false });
}

export function logout(): Promise<void> {
  return postJson<void>("/api/v1/auth/logout");
}

export function refresh(): Promise<TokenOut> {
  return postJson<TokenOut>("/api/v1/auth/refresh", undefined, { withCsrf: true });
}
