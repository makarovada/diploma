import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { NormalizationRuleCard } from "@/components/normalization-rule-card";
import { PageHeader } from "@/components/page-header";
import { normalizationRules } from "@/lib/mock-data";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";

export function ConnectionNormalizationPage() {
  const { connection, id, isLoading, isError } = useConnectionFromPath();
  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }
  return (
    <div className="space-y-4 p-4">
      <PageHeader title="Нормализация" description={`Правила для «${connection.name}»`} breadcrumbs="Интеграции / Подключения / Нормализация" />
      <ConnectionSubNav connectionId={id} />
      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-connection-normalization">
        {normalizationRules.map((r) => (
          <NormalizationRuleCard key={r.id} rule={r} />
        ))}
      </div>
    </div>
  );
}
