import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "wouter";
import { useAuth } from "@/app/auth-context";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { setStoredWorkspaceId } from "@/lib/api-client";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { postWorkspace } from "@/lib/api-workspaces";
import { queryKeys } from "@/lib/query-keys";
import { formatApiErrorMessage } from "@/lib/api-client";

export function WorkspacesPage() {
  const { refreshMe } = useAuth();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: async () => {
      const { items } = await fetchWorkspaces();
      return items;
    },
  });

  const createMut = useMutation({
    mutationFn: () => postWorkspace({ code: code.trim(), name: name.trim() }),
    onSuccess: async (data) => {
      setShowCreate(false);
      setCode("");
      setName("");
      setError(null);
      setStoredWorkspaceId(data.item.id);
      await qc.invalidateQueries({ queryKey: queryKeys.workspaces.list() });
      await refreshMe();
    },
    onError: (e) => setError(formatApiErrorMessage(e)),
  });

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError || !query.data) return <div className="p-4">Не удалось загрузить рабочие пространства.</div>;

  return (
    <div className="p-4">
      <PageHeader
        title="Рабочие пространства"
        description="Изоляция данных и доступов между командами"
        breadcrumbs="Администрирование / Рабочие пространства"
        actions={
          <Button data-testid="button-create-workspace" onClick={() => setShowCreate((v) => !v)}>
            Создать пространство
          </Button>
        }
      />

      {showCreate ? (
        <Card className="mb-4 p-4">
          <h3 className="mb-2 text-sm font-semibold">Новое пространство</h3>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              placeholder="код (латиница)"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              placeholder="Название"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Button type="button" disabled={!code.trim() || !name.trim() || createMut.isPending} onClick={() => createMut.mutate()}>
              Создать
            </Button>
          </div>
          {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
        </Card>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-workspaces">
        {query.data.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="state-empty-workspaces">
            Нет записей.
          </p>
        ) : (
          query.data.map((w) => (
            <Card key={w.id} className="p-4" data-testid={`card-workspace-${w.id}`}>
              <p className="font-semibold">{w.name}</p>
              <p className="text-xs text-muted-foreground">Код: {w.code}</p>
              <p className="text-sm">{w.is_admin ? "Администратор" : "Участник"}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  data-testid={`button-switch-workspace-${w.id}`}
                  onClick={() => {
                    setStoredWorkspaceId(w.id);
                    void refreshMe();
                  }}
                >
                  Переключиться
                </Button>
                {w.is_admin ? (
                  <Link href={`/workspaces/${w.id}/settings`}>
                    <Button variant="outline" size="sm" type="button">
                      Участники и права
                    </Button>
                  </Link>
                ) : null}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
