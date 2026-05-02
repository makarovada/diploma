import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { connectionStreamRows } from "@/lib/mock-data";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Card } from "@/components/ui/card";

export function ConnectionStreamsPage() {
  const { connection, id } = useConnectionFromPath();
  if (!connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }
  return (
    <div className="space-y-4 p-4">
      <PageHeader title="Потоки данных" description={connection.name} breadcrumbs="Интеграции / Подключения / Потоки" />
      <ConnectionSubNav connectionId={id} />
      <Card className="overflow-auto p-0" data-testid="table-connection-streams">
        <table className="w-full min-w-[800px] text-left text-sm" aria-label="Потоки">
          <thead className="bg-muted">
            <tr>
              <th>Поток</th>
              <th>Включён</th>
              <th>Режим sync</th>
              <th>Cursor</th>
              <th>Primary key</th>
              <th>Последний sync</th>
              <th>Записей</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {connectionStreamRows.map((s) => (
              <tr key={s.stream} className="border-t" data-testid={`row-stream-${s.stream}`}>
                <td>{s.stream}</td>
                <td>{s.enabled ? "Да" : "Нет"}</td>
                <td>{s.syncMode}</td>
                <td className="font-mono text-xs">{s.cursor}</td>
                <td className="font-mono text-xs">{s.primaryKey}</td>
                <td>{s.lastSync}</td>
                <td>{s.records}</td>
                <td>{s.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
