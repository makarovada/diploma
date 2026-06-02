import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/app/auth-context";
import { ApiError } from "@/lib/api-client";
import { postAuthRegister } from "@/lib/auth";
import { readNextFromRoutePath, safeReturnPath } from "@/lib/route-utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

type AuthMode = "login" | "register";
type RegistrationMode = "create_workspace" | "wait_for_invite";

function parseLoginError(e: unknown): string {
  if (e instanceof ApiError && e.status === 403) {
    try {
      const j = JSON.parse(e.body) as { detail?: string };
      if (typeof j.detail === "string") {
        return j.detail;
      }
    } catch {
      /* ignore */
    }
    return "Вход временно недоступен: у вас еще нет доступа к workspace.";
  }
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

function parseRegisterError(e: unknown): string {
  if (e instanceof ApiError) {
    try {
      const j = JSON.parse(e.body) as { detail?: { message?: string } | string };
      if (typeof j.detail === "string" && j.detail.trim()) {
        return j.detail;
      }
      if (typeof j.detail === "object" && j.detail !== null && typeof j.detail.message === "string") {
        return j.detail.message;
      }
    } catch {
      /* ignore */
    }
  }
  if (e instanceof Error) {
    return e.message;
  }
  return "Не удалось зарегистрироваться. Проверьте данные и повторите.";
}

export function LoginPage() {
  const [loc, setLocation] = useLocation();
  const { login, status, user } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [registrationMode, setRegistrationMode] = useState<RegistrationMode>("create_workspace");
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
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
          Войдите в существующий аккаунт или зарегистрируйте новый.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Button
            type="button"
            variant={mode === "login" ? "default" : "outline"}
            onClick={() => {
              setMode("login");
              setErr("");
              setInfo("");
            }}
            disabled={submitting}
          >
            Вход
          </Button>
          <Button
            type="button"
            variant={mode === "register" ? "default" : "outline"}
            onClick={() => {
              setMode("register");
              setErr("");
              setInfo("");
            }}
            disabled={submitting}
          >
            Регистрация
          </Button>
        </div>
        <form
          className="mt-4 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setErr("");
            setInfo("");
            const fd = new FormData(e.currentTarget);
            const username = String(fd.get("login") ?? "").trim();
            const email = String(fd.get("email") ?? "").trim();
            const password = String(fd.get("password") ?? "");
            const workspaceName = String(fd.get("workspace_name") ?? "").trim();
            const workspaceCode = String(fd.get("workspace_code") ?? "").trim();
            if (username.length < 1) {
              setErr("Введите логин.");
              return;
            }
            if (password.length < 1) {
              setErr("Введите пароль.");
              return;
            }
            if (mode === "register" && password.length < 8) {
              setErr("Пароль должен быть не короче 8 символов.");
              return;
            }
            if (mode === "register" && registrationMode === "create_workspace" && workspaceName.length < 1) {
              setErr("Введите название пространства.");
              return;
            }
            setSubmitting(true);
            try {
              if (mode === "login") {
                await login(username, password, readNextFromRoutePath(loc));
              } else {
                await postAuthRegister({
                  username,
                  email: email || null,
                  password,
                  registration_mode: registrationMode,
                  workspace_name: registrationMode === "create_workspace" ? workspaceName : undefined,
                  workspace_code: registrationMode === "create_workspace" ? workspaceCode || undefined : undefined,
                });
                if (registrationMode === "create_workspace") {
                  await login(username, password, readNextFromRoutePath(loc));
                } else {
                  setInfo("Аккаунт создан. Ожидайте, пока вас добавят в существующий workspace, затем войдите.");
                  setMode("login");
                }
              }
            } catch (e) {
              setErr(mode === "login" ? parseLoginError(e) : parseRegisterError(e));
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
              placeholder={mode === "login" ? "seed_analyst" : "new_user"}
              disabled={submitting}
            />
          </div>
          {mode === "register" ? (
            <div>
              <label className="text-sm" htmlFor="email">
                E-mail (опционально)
              </label>
              <Input id="email" name="email" type="email" autoComplete="email" className="mt-1" disabled={submitting} />
            </div>
          ) : null}
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
          {mode === "register" ? (
            <div className="space-y-2 rounded-md border p-3">
              <p className="text-sm font-medium">Вариант подключения к workspace</p>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="registration_mode"
                  checked={registrationMode === "create_workspace"}
                  onChange={() => setRegistrationMode("create_workspace")}
                  disabled={submitting}
                />
                <span>Создать свое пространство</span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="registration_mode"
                  checked={registrationMode === "wait_for_invite"}
                  onChange={() => setRegistrationMode("wait_for_invite")}
                  disabled={submitting}
                />
                <span>Ждать добавления в существующее пространство</span>
              </label>
            </div>
          ) : null}
          {mode === "register" && registrationMode === "create_workspace" ? (
            <>
              <div>
                <label className="text-sm" htmlFor="workspace_name">
                  Название пространства
                </label>
                <Input id="workspace_name" name="workspace_name" className="mt-1" disabled={submitting} />
              </div>
              <div>
                <label className="text-sm" htmlFor="workspace_code">
                  Код пространства (опционально)
                </label>
                <Input id="workspace_code" name="workspace_code" className="mt-1" placeholder="my-team" disabled={submitting} />
              </div>
            </>
          ) : null}
          {err ? (
            <p className="text-sm text-destructive" data-testid="login-error">
              {err}
            </p>
          ) : null}
          {info ? <p className="text-sm text-emerald-700">{info}</p> : null}
          <Button type="submit" className="w-full" data-testid="button-login-submit" disabled={submitting}>
            {submitting ? "Отправка…" : mode === "login" ? "Войти" : "Зарегистрироваться"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
