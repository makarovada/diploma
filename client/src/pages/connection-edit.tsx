import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";

export function ConnectionEditPage() {
  const { connection, id, isLoading, isError } = useConnectionFromPath();
  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4" data-testid="state-not-found-connection">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }
  return (
    <div className="space-y-4 p-4">
      <PageHeader title={`Редактирование: ${connection.name}`} description="Название, описание и метаданные" breadcrumbs="Интеграции / Подключения / Редактирование" />
      <ConnectionSubNav connectionId={id} />
      <div className="max-w-lg space-y-2 rounded-lg border bg-card p-4" data-testid="form-connection-edit">
        <label className="text-sm" htmlFor="conn-name">
          Название
        </label>
        <Input id="conn-name" defaultValue={connection.name} data-testid="input-connection-edit-name" />
        <label className="text-sm" htmlFor="conn-desc">
          Описание
        </label>
        <Input id="conn-desc" placeholder="Назначение потока" data-testid="input-connection-edit-desc" />
        <Button type="button" data-testid="button-save-connection-edit">
          Сохранить
        </Button>
      </div>
    </div>
  );
}
