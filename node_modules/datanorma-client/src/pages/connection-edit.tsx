import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { deleteEltConnection, patchEltConnection } from "@/lib/api-elt";
import { formatApiErrorMessage } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";

export function ConnectionEditPage() {
  const { connection, detail, id, workspaceCode, isLoading, isError } = useConnectionFromPath();
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!detail) return;
    setName(detail.name);
    setDescription(detail.description ?? "");
  }, [detail]);

  const saveMut = useMutation({
    mutationFn: () =>
      patchEltConnection(Number(id), {
        workspace_code: workspaceCode,
        name: name.trim() || connection?.name,
        description: description.trim() ? description.trim() : null,
      }),
    onSuccess: () => {
      setErr(null);
      setSaveMsg("Сохранено");
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltDetail(id, workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.detail(id) });
    },
    onError: (e: unknown) => {
      setSaveMsg(null);
      setErr(formatApiErrorMessage(e, "Ошибка сохранения"));
    },
  });

  if (isLoading) {
    return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  }
  if (isError || !connection) {
    return (
      <div className="p-4" data-testid="state-not-found-connection">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={`Редактирование: ${connection.name}`}
        description="Название, описание и ссылки на потоки, расписание и маппинг"
        breadcrumbs="Интеграции / Подключения / Редактирование"
        actions={
          <ConfirmDeleteButton
            entityLabel={connection.name}
            testId="button-delete-connection-edit"
            onDelete={() => deleteEltConnection(Number(id), workspaceCode)}
            onSuccess={() => {
              void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
              setLocation("/connections");
            }}
          />
        }
      />
      <ConnectionSubNav connectionId={id} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="max-w-lg space-y-3 p-4" data-testid="form-connection-edit">
          <label className="text-sm" htmlFor="conn-name">
            Название
          </label>
          <Input
            id="conn-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            data-testid="input-connection-edit-name"
          />
          <label className="text-sm" htmlFor="conn-desc">
            Описание
          </label>
          <Input
            id="conn-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Назначение потока"
            data-testid="input-connection-edit-desc"
          />
          {saveMsg ? (
            <p className="text-sm text-muted-foreground" data-testid="text-connection-edit-saved">
              {saveMsg}
            </p>
          ) : null}
          {err ? (
            <p className="text-sm text-destructive" data-testid="text-connection-edit-error">
              {err}
            </p>
          ) : null}
          <Button
            type="button"
            data-testid="button-save-connection-edit"
            disabled={saveMut.isPending}
            onClick={() => saveMut.mutate()}
          >
            Сохранить
          </Button>
        </Card>
        <Card className="space-y-2 p-4 text-sm" data-testid="connection-edit-links">
          <p className="font-medium">Дополнительные настройки</p>
          <p className="text-muted-foreground">
            Расписание, режимы потоков и маппинг колонок настраиваются в отдельных разделах подключения.
          </p>
          <div className="flex flex-wrap gap-2">
            <LinkAsButton href={`/connections/${id}/settings`} variant="outline" data-testid="link-connection-edit-settings">
              Расписание
            </LinkAsButton>
            <LinkAsButton href={`/connections/${id}/streams`} variant="outline" data-testid="link-connection-edit-streams">
              Потоки
            </LinkAsButton>
            <LinkAsButton href={`/connections/${id}/streams/edit`} variant="outline" data-testid="link-connection-edit-mapping">
              Потоки и маппинг
            </LinkAsButton>
          </div>
        </Card>
      </div>
    </div>
  );
}
