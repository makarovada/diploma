import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Card } from "@/components/ui/card";
import {
  describeReplicationPreset,
  parseCursorFields,
  parsePrimaryKeyFields,
  replicationPresetFromFields,
} from "@/lib/destination-sync-mode";
import type { Status } from "@/lib/types";

export function ConnectionStreamsPage() {
  const { connection, detail, id, isLoading, isError } = useConnectionFromPath();
  const streams = detail?.streams ?? [];

  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  const streamRows = streams.map((s) => ({
    stream: s.stream_name,
    enabled: s.is_enabled,
    replication: describeReplicationPreset(
      replicationPresetFromFields(s.sync_mode, s.destination_sync_mode ?? undefined),
    ),
    cursorField: parseCursorFields(s.cursor_field).join(", ") || "—",
    primaryKey: parsePrimaryKeyFields(s.primary_key).join(", ") || "—",
    cursor: s.cursor_value != null ? String(s.cursor_value) : "—",
    status: (s.is_enabled ? "ready" : "pending") as Status,
  }));

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Потоки данных"
        description={connection.name}
        breadcrumbs="Интеграции / Подключения / Потоки"
        actions={
          <LinkAsButton href={`/connections/${id}/streams/edit`} data-testid="link-edit-connection-streams">
            Редактировать потоки
          </LinkAsButton>
        }
      />
      <ConnectionSubNav connectionId={id} />
      <Card className="overflow-auto p-0" data-testid="table-connection-streams">
        <table className="w-full min-w-[900px] text-left text-sm" aria-label="Потоки">
          <thead className="bg-muted">
            <tr>
              <th>Поток</th>
              <th>Включён</th>
              <th>Режим передачи</th>
              <th>Курсор</th>
              <th>Первичный ключ</th>
              <th>Значение курсора</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {streamRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-4 text-muted-foreground">
                  Нет потоков
                </td>
              </tr>
            ) : (
              streamRows.map((s) => (
                <tr key={s.stream} className="border-t" data-testid={`row-stream-${s.stream}`}>
                  <td>{s.stream}</td>
                  <td>{s.enabled ? "Да" : "Нет"}</td>
                  <td>{s.replication}</td>
                  <td className="font-mono text-xs">{s.cursorField}</td>
                  <td className="font-mono text-xs">{s.primaryKey}</td>
                  <td className="font-mono text-xs">{s.cursor}</td>
                  <td>
                    <StatusBadge status={s.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
