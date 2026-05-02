import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export function LoginPage() {
  const [, setLocation] = useLocation();
  const [err, setErr] = useState("");

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4" data-testid="page-login">
      <Card className="w-full max-w-md p-6">
        <h1 className="text-xl font-semibold">Вход в DataNorma</h1>
        <p className="mt-1 text-sm text-muted-foreground">Демо: любой логин и пароль для перехода в приложение.</p>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setErr("");
            const fd = new FormData(e.currentTarget);
            const u = String(fd.get("login") ?? "");
            if (u.length < 2) {
              setErr("Введите логин (минимум 2 символа).");
              return;
            }
            setLocation("/onboarding");
          }}
        >
          <div>
            <label className="text-sm" htmlFor="login">
              Логин
            </label>
            <Input id="login" name="login" autoComplete="username" className="mt-1" data-testid="input-login-email" placeholder="email@company.ru" />
          </div>
          <div>
            <label className="text-sm" htmlFor="password">
              Пароль
            </label>
            <Input id="password" name="password" type="password" autoComplete="current-password" className="mt-1" data-testid="input-login-password" />
          </div>
          {err ? (
            <p className="text-sm text-destructive" data-testid="login-error">
              {err}
            </p>
          ) : null}
          <Button type="submit" className="w-full" data-testid="button-login-submit">
            Войти
          </Button>
        </form>
      </Card>
    </div>
  );
}
