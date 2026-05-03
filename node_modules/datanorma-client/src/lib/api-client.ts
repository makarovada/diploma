/**
 * HTTP-клиент для REST API. Auth: Bearer из localStorage; для dev Vite проксирует /api → backend.
 */
const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export const TOKEN_STORAGE_KEY = "datanorma_access_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    /* ignore */
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type ApiRequestInit = RequestInit & { skipAuth?: boolean; suppressGlobalAuthHandlers?: boolean };

type AuthHandlers = {
  on401: () => void;
  on403: (body: string) => void;
};

let authHandlers: AuthHandlers = {
  on401: () => {},
  on403: () => {},
};

/** Регистрируется из AuthProvider: редирект на /login и /forbidden. */
export function configureApiAuth(handlers: Partial<AuthHandlers>): void {
  authHandlers = { ...authHandlers, ...handlers };
}

function joinUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

function buildHeaders(init: ApiRequestInit): Headers {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (!init.skipAuth) {
    const t = getStoredToken();
    if (t) {
      headers.set("Authorization", `Bearer ${t}`);
    }
  }
  return headers;
}

async function handleResponse(res: Response, sentBearer: boolean, init: ApiRequestInit): Promise<string> {
  const text = await res.text();
  const notify = sentBearer && !init.suppressGlobalAuthHandlers;
  if (res.status === 401) {
    if (notify) {
      authHandlers.on401();
    }
    throw new ApiError(res.statusText || "Unauthorized", 401, text);
  }
  if (res.status === 403) {
    if (notify) {
      authHandlers.on403(text);
    }
    throw new ApiError(res.statusText || "Forbidden", 403, text);
  }
  if (!res.ok) {
    throw new ApiError(res.statusText || "Request failed", res.status, text);
  }
  return text;
}

export async function apiGetJson<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const headers = buildHeaders(init);
  const sentBearer = headers.has("Authorization");
  const res = await fetch(joinUrl(path), {
    ...init,
    headers,
  });
  const text = await handleResponse(res, sentBearer, init);
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export async function apiPostJson<T, B = unknown>(path: string, body: B, init: ApiRequestInit = {}): Promise<T> {
  const headers = buildHeaders(init);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const sentBearer = headers.has("Authorization");
  const res = await fetch(joinUrl(path), {
    method: "POST",
    ...init,
    headers,
    body: JSON.stringify(body),
  });
  const text = await handleResponse(res, sentBearer, init);
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export async function apiPatchJson<T, B = unknown>(path: string, body: B, init: ApiRequestInit = {}): Promise<T> {
  const headers = buildHeaders(init);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const sentBearer = headers.has("Authorization");
  const res = await fetch(joinUrl(path), {
    method: "PATCH",
    ...init,
    headers,
    body: JSON.stringify(body),
  });
  const text = await handleResponse(res, sentBearer, init);
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export type ApiJsonRequestInit = ApiRequestInit & { json?: unknown };

/** Унифицированный JSON-запрос: GET по умолчанию; для POST/PATCH передайте `method` и `json`. */
export async function apiRequest<T>(path: string, init: ApiJsonRequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  if (method === "GET" || method === "HEAD") {
    return apiGetJson<T>(path, init);
  }
  if (init.json === undefined) {
    throw new Error("apiRequest: для POST/PUT/PATCH укажите init.json (тело)");
  }
  const { json, ...rest } = init;
  return apiPostJson<T, unknown>(path, json, rest);
}
