import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function DestinationNewPage() {
  return (
    <div className="p-4">
      <PageHeader title="Новый приёмник" description="PostgreSQL, ClickHouse, CSV или другой тип" breadcrumbs="Интеграции / Приёмники / Новый" />
      <div className="max-w-md space-y-2" data-testid="form-new-destination">
        <Input placeholder="Название" data-testid="input-destination-name" />
        <Input placeholder="Хост" data-testid="input-destination-host" />
        <Input placeholder="База / схема" data-testid="input-destination-db" />
        <div className="flex gap-2">
          <Button data-testid="button-save-destination">Сохранить</Button>
          <LinkAsButton href="/destinations" variant="outline" data-testid="button-cancel-destination">Отмена</LinkAsButton>
        </div>
      </div>
    </div>
  );
}
