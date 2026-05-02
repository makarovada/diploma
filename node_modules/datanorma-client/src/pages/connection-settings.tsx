import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Card } from "@/components/ui/card";

export function ConnectionSettingsPage() {
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
      <PageHeader title="Настройки подключения" description={connection.name} breadcrumbs="Интеграции / Подключения / Настройки" />
      <ConnectionSubNav connectionId={id} />
      <Card className="max-w-xl space-y-3 p-4" data-testid="form-connection-settings">
        <p className="text-sm font-medium">Расписание</p>
        <label className="text-xs text-muted-foreground" htmlFor="cron">
          Cron / пресет
        </label>
        <Input id="cron" defaultValue="0 3 * * * (ежедневно 03:00)" data-testid="input-connection-schedule" />
        <p className="text-xs text-muted-foreground">Часовой пояс: Europe/Moscow</p>
        <div className="flex gap-2">
          <Button type="button" data-testid="button-save-connection-settings">
            Сохранить
          </Button>
          <Button type="button" variant="outline" data-testid="button-disable-schedule">
            Отключить расписание
          </Button>
        </div>
      </Card>
    </div>
  );
}
