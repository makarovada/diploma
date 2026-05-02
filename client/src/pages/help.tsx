import { PageHeader } from "@/components/page-header";
import { PageFooter } from "@/components/page-footer";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";

export function HelpPage() {
  return (
    <div className="p-4">
      <PageHeader title="Помощь" description="Быстрые ответы и ссылки на документацию" breadcrumbs="Сервис / Помощь" />
      <Card className="space-y-3 p-4">
        <p className="text-sm">Создание подключения, маппинг и нормализация описаны в внутренней документации MVP.</p>
        <ul className="list-inside list-disc text-sm text-muted-foreground">
          <li>Проверяйте доступ к источнику перед первым запуском.</li>
          <li>Обязательные поля канонической модели должны быть сопоставлены.</li>
          <li>Проблемные записи можно разбирать из раздела «Проблемные записи».</li>
        </ul>
        <LinkAsButton href="/api-docs" variant="outline" data-testid="button-help-to-api-docs">
          Документация API
        </LinkAsButton>
      </Card>
      <PageFooter />
    </div>
  );
}
