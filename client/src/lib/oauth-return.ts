/**
 * OAuth callback для hash-router (wouter useHashLocation).
 * Google redirect должен вести на `origin/#/path?google_oauth_state=…`, не на `/path` без hash.
 */

export const OAUTH_WIZARD_RESTORE_KEY = "datanorma_oauth_wizard_restore_v1";
export const OAUTH_DESTINATION_RESTORE_KEY = "datanorma_oauth_destination_restore_v1";

export type GoogleOAuthCallbackParams = {
  state: string | null;
  error: string | null;
};

/** Текущий маршрут SPA для return_url: `/connections/new?source=1` */
export function currentSpaReturnPath(): string {
  if (typeof window === "undefined") return "/";
  const fromHash = window.location.hash.replace(/^#/, "");
  if (fromHash) return fromHash.startsWith("/") ? fromHash : `/${fromHash}`;
  const path = window.location.pathname || "/";
  const search = window.location.search || "";
  if (path !== "/" && path !== "/index.html") {
    return `${path}${search}`;
  }
  return search ? `/${search.replace(/^\?/, "")}` : "/";
}

/** Полный URL возврата после Google OAuth */
export function buildOAuthReturnUrl(): string {
  const path = currentSpaReturnPath();
  return `${window.location.origin}/#${path}`;
}

const OAUTH_COMPLETE_GUARD_PREFIX = "datanorma_google_oauth_completed:";

/** Уже обрабатывали этот state (React StrictMode вызывает effect дважды). */
export function isGoogleOAuthStateAlreadyCompleted(state: string): boolean {
  try {
    return sessionStorage.getItem(`${OAUTH_COMPLETE_GUARD_PREFIX}${state}`) === "1";
  } catch {
    return false;
  }
}

export function markGoogleOAuthStateCompleted(state: string): void {
  try {
    sessionStorage.setItem(`${OAUTH_COMPLETE_GUARD_PREFIX}${state}`, "1");
  } catch {
    /* ignore */
  }
}

/**
 * Backend редиректит на `/connections/new?google_oauth_state=…` без hash.
 * Wouter ждёт `#/connections/new?…` — переносим query в hash до роутинга.
 */
function peekSavedOAuthReturnPath(): string | null {
  try {
    const raw = sessionStorage.getItem(OAUTH_WIZARD_RESTORE_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as { returnPath?: string };
    const p = saved.returnPath?.trim();
    if (!p) return null;
    const q = p.indexOf("?");
    return (q >= 0 ? p.slice(0, q) : p) || null;
  } catch {
    return null;
  }
}

export function migrateOAuthCallbackToHashRouter(): void {
  if (typeof window === "undefined") return;

  const search = window.location.search || "";
  const sp = new URLSearchParams(search);
  if (!sp.get("google_oauth_state") && !sp.get("google_oauth_error")) {
    return;
  }

  const hashBody = window.location.hash.replace(/^#/, "");
  if (
    hashBody.includes("google_oauth_state=") ||
    hashBody.includes("google_oauth_error=")
  ) {
    return;
  }

  let path = window.location.pathname || "/";
  if (path.endsWith("/index.html")) {
    path = path.slice(0, -"/index.html".length) || "/";
  }
  if (path.startsWith("/ui")) {
    path = path.slice(3) || "/";
  }

  let route: string;
  if (path === "/" || path === "") {
    const fallback = peekSavedOAuthReturnPath() || "/connections/new";
    route = `${fallback}${search}`;
  } else {
    route = `${path}${search}`;
  }
  const normalized = route.startsWith("/") ? route : `/${route}`;
  window.location.replace(`${window.location.origin}/#${normalized}`);
}

/** Исправить hash, если OAuth попал в «ломаный» путь вроде `/google_oauth_state=…`. */
export function repairOAuthLandingHash(): void {
  if (typeof window === "undefined") return;

  const path = currentHashPathOnly();
  if (!path.includes("google_oauth") && path !== "/") {
    return;
  }
  if (!hasGoogleOAuthCallback()) {
    return;
  }

  const fallback = peekSavedOAuthReturnPath() || "/connections/new";
  const origin = window.location.origin;
  const { state, error } = readGoogleOAuthCallbackParams();
  const qs = new URLSearchParams();
  if (state) qs.set("google_oauth_state", state);
  if (error) qs.set("google_oauth_error", error);
  const q = qs.toString();
  window.location.replace(`${origin}/#${fallback}${q ? `?${q}` : ""}`);
}

function queryFromHash(): URLSearchParams {
  const hash = window.location.hash.replace(/^#/, "");
  const qs = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  return new URLSearchParams(qs);
}

export function readGoogleOAuthCallbackParams(): GoogleOAuthCallbackParams {
  const fromHash = queryFromHash();
  const fromSearch = new URLSearchParams(window.location.search);
  return {
    state: fromHash.get("google_oauth_state") || fromSearch.get("google_oauth_state"),
    error: fromHash.get("google_oauth_error") || fromSearch.get("google_oauth_error"),
  };
}

export function hasGoogleOAuthCallback(): boolean {
  const { state, error } = readGoogleOAuthCallbackParams();
  if (state || error) return true;
  try {
    return Boolean(sessionStorage.getItem(PENDING_OAUTH_STATE_KEY));
  } catch {
    return false;
  }
}

const PENDING_OAUTH_STATE_KEY = "datanorma_pending_google_oauth_state";
const PENDING_OAUTH_ERROR_KEY = "datanorma_pending_google_oauth_error";

/** Забрать state из URL в sessionStorage и оставить в hash только путь (для wouter). */
export function stashGoogleOAuthParamsFromUrl(): void {
  const { state, error } = readGoogleOAuthCallbackParams();
  if (!state && !error) return;
  try {
    if (state) sessionStorage.setItem(PENDING_OAUTH_STATE_KEY, state);
    if (error) sessionStorage.setItem(PENDING_OAUTH_ERROR_KEY, error);
  } catch {
    /* ignore */
  }
  stripGoogleOAuthParamsFromLocation();
}

export function takePendingGoogleOAuthState(): string | null {
  try {
    const s = sessionStorage.getItem(PENDING_OAUTH_STATE_KEY);
    if (s) sessionStorage.removeItem(PENDING_OAUTH_STATE_KEY);
    return s;
  } catch {
    return null;
  }
}

export function takePendingGoogleOAuthError(): string | null {
  try {
    const e = sessionStorage.getItem(PENDING_OAUTH_ERROR_KEY);
    if (e) sessionStorage.removeItem(PENDING_OAUTH_ERROR_KEY);
    return e;
  } catch {
    return null;
  }
}

/** Путь hash без query — для сопоставления с Route в wouter */
export function currentHashPathOnly(): string {
  const full = currentSpaReturnPath();
  const q = full.indexOf("?");
  const path = q >= 0 ? full.slice(0, q) : full;
  return path.startsWith("/") ? path : `/${path}`;
}

/** Убрать oauth-параметры из hash (и из search, если попали туда по ошибке) */
export function stripGoogleOAuthParamsFromLocation(): void {
  if (typeof window === "undefined") return;

  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    const qIdx = hash.indexOf("?");
    const pathPart = qIdx >= 0 ? hash.slice(0, qIdx) : hash;
    const sp = new URLSearchParams(qIdx >= 0 ? hash.slice(qIdx + 1) : "");
    sp.delete("google_oauth_state");
    sp.delete("google_oauth_error");
    const rest = sp.toString();
    const nextHash = rest ? `#${pathPart}?${rest}` : pathPart ? `#${pathPart}` : "#/";
    const url = new URL(window.location.href);
    url.hash = nextHash;
    url.searchParams.delete("google_oauth_state");
    url.searchParams.delete("google_oauth_error");
    window.history.replaceState({}, "", url.toString());
    return;
  }

  const url = new URL(window.location.href);
  url.searchParams.delete("google_oauth_state");
  url.searchParams.delete("google_oauth_error");
  window.history.replaceState({}, "", url.toString());
}
