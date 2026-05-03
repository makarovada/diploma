import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/app/auth-context";
import { ApiError } from "@/lib/api-client";
import { readNextFromRoutePath, safeReturnPath } from "@/lib/route-utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

function parseLoginError(e: unknown): string {
  if (e instanceof ApiError && e.status === 401) {
    try {
      const j = JSON.parse(e.body) as { detail?: string };
      if (typeof j.detail === "string") {
        return j.detail;
      }
    } catch {
      /* ignore */
    }
    return "Неверный логин или пароль.";
  }
  if (e instanceof Error) {
    return e.message;
  }
  return "Не удалось войти. Проверьте сеть и повторите.";
}

export function LoginPage() {
  const [loc, setLocation] = useLocation();
  const { login, status, user } = useAuth();
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated" && user) {
      setLocation(safeReturnPath(readNextFromRoutePath(loc)));
    }
  }, [status, user, loc, setLocation]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4" data-testid="page-login">
      <Card className="w-full max-w-md p-6">
        <h1 className="text-xl font-semibold">Вход в DataNorma</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Используйте учётную запись из сидов БД (например seed_analyst / AnalystDemo2026) или Jinja&nbsp;/app/login.
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setErr("");
            const fd = new FormData(e.currentTarget);
            const username = String(fd.get("login") ?? "").trim();
            const password = String(fd.get("password") ?? "");
            if (username.length < 1) {
              setErr("Введите логин.");
              return;
            }
            if (password.length < 1) {
              setErr("Введите пароль.");
              return;
            }
            setSubmitting(true);
            try {
              await login(username, password, readNextFromRoutePath(loc));
            } catch (ex) {
              setErr(parseLoginError(ex));
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <div>
            <label className="text-sm" htmlFor="login">
              Логин
            </label>
            <Input
              id="login"
              name="login"
              autoComplete="username"
              className="mt-1"
              data-testid="input-login-email"
              placeholder="seed_analyst"
              disabled={submitting}
            />
          </div>
          <div>
            <label className="text-sm" htmlFor="password">
              Пароль
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              className="mt-1"
              data-testid="input-login-password"
              disabled={submitting}
            />
          </div>
          {err ? (
            <p className="text-sm text-destructive" data-testid="login-error">
              {err}
            </p>
          ) : null}
          <Button type="submit" className="w-full" data-testid="button-login-submit" disabled={submitting}>
            {submitting ? "Вход…" : "Войти"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
