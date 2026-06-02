import { useEffect } from "react";
import { useAuth } from "@/app/auth-context";
import { LinkAsButton } from "@/components/link-as-button";
import { Card } from "@/components/ui/card";

export function ForbiddenPage() {
  const { forbiddenMessage, clearForbiddenMessage, user } = useAuth();

  useEffect(() => {
    return () => clearForbiddenMessage();
  }, [clearForbiddenMessage]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4" data-testid="page-forbidden">
      <Card className="w-full max-w-md p-6 text-center">
        <h1 className="text-xl font-semibold">403 — доступ запрещён</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {forbiddenMessage ?? "У вашей роли недостаточно прав для этого действия."}
        </p>
        {user ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Вы вошли как <span className="font-medium text-foreground">{user.username}</span>
          </p>
        ) : null}
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <LinkAsButton href="/">На дашборд</LinkAsButton>
          <LinkAsButton href="/connections" variant="outline">
            Подключения
          </LinkAsButton>
        </div>
      </Card>
    </div>
  );
}
