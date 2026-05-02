import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LogViewer } from "@/components/log-viewer";
import { PageHeader } from "@/components/page-header";
import { runLogsExtended } from "@/lib/mock-data";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";

export function ConnectionLogsPage() {
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
      <PageHeader title="Логи" description={`Последний запуск · ${connection.name}`} breadcrumbs="Интеграции / Подключения / Логи" />
      <ConnectionSubNav connectionId={id} />
      <LogViewer logs={runLogsExtended} />
    </div>
  );
}
