import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Card } from "@/components/ui/card";
import { ScheduleEditor } from "@/components/schedule-editor";
import { deleteEltConnection, patchEltConnection } from "@/lib/api-elt";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { useLocation } from "wouter";
import { describeCronExpression } from "@/lib/schedule-config";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/lib/api-client";

export function ConnectionSettingsPage() {
  const { connection, detail, id, workspaceCode, isLoading, isError } = useConnectionFromPath();
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [cron, setCron] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [scheduleReady, setScheduleReady] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!detail) return;
    setCron(detail.schedule_cron?.trim() ?? "");
    setTimezone(detail.timezone?.trim() || "UTC");
    setScheduleReady(true);
  }, [detail]);

  const saveMut = useMutation({
    mutationFn: () =>
      patchEltConnection(Number(id), {
        workspace_code: workspaceCode,
        schedule_cron: cron.trim() ? cron.trim() : null,
        timezone: timezone.trim() || "UTC",
      }),
    onSuccess: () => {
      setErr(null);
      setSaveMsg("Сохранено");
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltDetail(id, workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: ["schedules", "v1"] });
    },
    onError: (e: unknown) => {
      setSaveMsg(null);
      setErr(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Ошибка сохранения");
    },
  });

  const disableScheduleMut = useMutation({
    mutationFn: () =>
      patchEltConnection(Number(id), {
        workspace_code: workspaceCode,
        schedule_cron: null,
      }),
    onSuccess: () => {
      setCron("");
      setErr(null);
      setSaveMsg("Расписание отключено");
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltDetail(id, workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: ["schedules", "v1"] });
    },
    onError: (e: unknown) => {
      setSaveMsg(null);
      setErr(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Ошибка");
    },
  });

  if (isLoading || !scheduleReady) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Настройки подключения"
        description={connection.name}
        breadcrumbs="Интеграции / Подключения / Настройки"
        actions={
          <div className="flex flex-wrap gap-2">
            <LinkAsButton href={`/connections/${id}/edit`} variant="outline" data-testid="button-edit-connection-settings">
              Изменить
            </LinkAsButton>
            <ConfirmDeleteButton
              entityLabel={connection.name}
              testId="button-delete-connection-settings"
              onDelete={() => deleteEltConnection(Number(id), workspaceCode)}
              onSuccess={() => {
                void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
                setLocation("/connections");
              }}
            />
          </div>
        }
      />
      <ConnectionSubNav connectionId={id} />
      <Card className="max-w-2xl space-y-4 p-4" data-testid="form-connection-settings">
        <div>
          <p className="text-sm font-medium">Расписание синхронизации</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Автозапуск выполняется планировщиком в процессе API (проверка раз в минуту; также дублируется Dagster
            sensor <code className="font-mono">connection_cron_sensor</code>). Пустое расписание — только ручной запуск.
          </p>
          {cron.trim() ? (
            <p className="mt-2 text-sm text-muted-foreground" data-testid="text-connection-settings-current-schedule">
              Текущее: {describeCronExpression(cron, timezone)}
              <span className="ml-1 font-mono text-xs">({cron.trim()})</span>
            </p>
          ) : null}
        </div>
        {scheduleReady ? (
          <ScheduleEditor
            key={`${id}-${cron}-${timezone}`}
            cron={cron}
            timezone={timezone}
            testIdPrefix="connection-settings"
            onCronChange={setCron}
            onTimezoneChange={setTimezone}
          />
        ) : null}
        {saveMsg ? (
          <p className="text-sm text-muted-foreground" data-testid="text-connection-settings-save">
            {saveMsg}
          </p>
        ) : null}
        {err ? (
          <p className="text-sm text-destructive" data-testid="text-connection-settings-error">
            {err}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="button" data-testid="button-save-connection-settings" disabled={saveMut.isPending} onClick={() => saveMut.mutate()}>
            Сохранить
          </Button>
          <Button
            type="button"
            variant="outline"
            data-testid="button-disable-schedule"
            disabled={disableScheduleMut.isPending || !cron.trim()}
            onClick={() => disableScheduleMut.mutate()}
          >
            Отключить расписание
          </Button>
        </div>
      </Card>
    </div>
  );
}
