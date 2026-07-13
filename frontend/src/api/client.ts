import { getCsrfToken } from "@/utils/csrf";

export interface ErrorOut {
  code: string;
  message: string;
  detail: Record<string, unknown>;
}

export class ApiError extends Error {
  code: string;
  detail: Record<string, unknown>;
  status: number;

  constructor(status: number, code: string, message: string, detail: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return undefined as T;
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = data as ErrorOut | null;
    const code = err?.code ?? "UNKNOWN";
    const message = err?.message ?? `HTTP ${res.status}`;
    const detail = err?.detail ?? {};

    if (res.status === 401 && code === "AUTH_REQUIRED") {
      onUnauthorized?.();
    }

    throw new ApiError(res.status, code, message, detail);
  }

  return data as T;
}

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  return headers;
}

function buildHeadersWithCsrf(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const csrf = getCsrfToken();
  if (csrf) {
    headers["X-CSRF-Token"] = csrf;
  }
  return headers;
}

export async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: buildHeaders(),
  });
  return handleResponse<T>(res);
}

export async function postJson<T>(
  url: string,
  body?: unknown,
  options?: { withCsrf?: boolean },
): Promise<T> {
  const withCsrf = options?.withCsrf ?? true;
  const headers = withCsrf
    ? buildHeadersWithCsrf({ "Content-Type": "application/json" })
    : buildHeaders({ "Content-Type": "application/json" });

  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function patchJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "PATCH",
    credentials: "include",
    headers: buildHeadersWithCsrf({ "Content-Type": "application/json" }),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function deleteJson<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    method: "DELETE",
    credentials: "include",
    headers: buildHeadersWithCsrf(),
  });
  return handleResponse<T>(res);
}

export async function upload<T>(url: string, formData: FormData): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: buildHeadersWithCsrf(),
    body: formData,
  });
  return handleResponse<T>(res);
}
