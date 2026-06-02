import { type PropsWithChildren, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import {
  ApiError,
  clearStoredToken,
  clearStoredWorkspaceId,
  configureApiAuth,
  getStoredToken,
  getStoredWorkspaceId,
  setStoredToken,
  setStoredWorkspaceId,
} from "@/lib/api-client";
import { fetchAuthMe, postAuthLogin } from "@/lib/auth";
import type { MeDto } from "@/lib/api-types";
import { hasGoogleOAuthCallback } from "@/lib/oauth-return";
import { currentHashRoutePath, safeReturnPath } from "@/lib/route-utils";

export type MeUser = MeDto;

type LoginResponse = {
  access_token: string;
  token_type: string;
};

type AuthStatus = "initializing" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  user: MeUser | null;
  status: AuthStatus;
  forbiddenMessage: string | null;
  clearForbiddenMessage: () => void;
  login: (username: string, password: string, returnTo?: string | null) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function parse403Message(body: string): string {
  try {
    const j = JSON.parse(body) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === "object" && d !== null && "message" in d && typeof (d as { message: string }).message === "string") {
      return (d as { message: string }).message;
    }
    if (typeof d === "string") {
      return d;
    }
  } catch {
    /* ignore */
  }
  return "Недостаточно прав для этой операции.";
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [, setLocation] = useLocation();
  const [user, setUser] = useState<MeUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [forbiddenMessage, setForbiddenMessage] = useState<string | null>(null);

  const logout = useCallback(() => {
    clearStoredToken();
    clearStoredWorkspaceId();
    setUser(null);
    setStatus("unauthenticated");
    setLocation("/login");
  }, [setLocation]);

  const syncWorkspaceStorageWithMe = useCallback((me: MeUser) => {
    const ids = new Set((me.workspaces ?? []).map((w) => w.id));
    const stored = getStoredWorkspaceId();
    if (stored !== null && ids.has(stored)) {
      return;
    }
    const fallback = me.active_workspace_id ?? (me.workspaces ?? [])[0]?.id;
    if (fallback !== undefined && fallback !== null) {
      setStoredWorkspaceId(fallback);
    }
  }, []);

  const refreshMe = useCallback(async () => {
    const t = getStoredToken();
    if (!t) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }
    const me = await fetchAuthMe();
    syncWorkspaceStorageWithMe(me);
    setUser(me);
    setStatus("authenticated");
  }, [syncWorkspaceStorageWithMe]);

  useEffect(() => {
    configureApiAuth({
      on401: () => {
        if (hasGoogleOAuthCallback()) {
          return;
        }
        clearStoredToken();
        clearStoredWorkspaceId();
        setUser(null);
        setStatus("unauthenticated");
        const path = currentHashRoutePath();
        const next = encodeURIComponent(path === "/login" ? "/" : path);
        setLocation(`/login?next=${next}`);
      },
      on403: (body) => {
        setForbiddenMessage(parse403Message(body));
        setLocation("/forbidden");
      },
    });
  }, [setLocation]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const t = getStoredToken();
      if (!t) {
        if (!cancelled) {
          setStatus("unauthenticated");
        }
        return;
      }
      try {
        const me = await fetchAuthMe();
        if (!cancelled) {
          setUser(me);
          setStatus("authenticated");
        }
      } catch (e) {
        if (!cancelled) {
          if (e instanceof ApiError && e.status === 401) {
            clearStoredToken();
          }
          setUser(null);
          setStatus("unauthenticated");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (username: string, password: string, returnTo?: string | null) => {
      const data = (await postAuthLogin(username, password)) as LoginResponse;
      setStoredToken(data.access_token);
      await refreshMe();
      setLocation(safeReturnPath(returnTo));
    },
    [refreshMe, setLocation],
  );

  const clearForbiddenMessage = useCallback(() => setForbiddenMessage(null), []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      forbiddenMessage,
      clearForbiddenMessage,
      login,
      logout,
      refreshMe,
    }),
    [user, status, forbiddenMessage, clearForbiddenMessage, login, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
