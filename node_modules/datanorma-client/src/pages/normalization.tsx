import { normalizationRules } from "@/lib/mock-data";
import { NormalizationRuleCard } from "@/components/normalization-rule-card";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LinkAsButton } from "@/components/link-as-button";

export function NormalizationPage() {
  return (
    <div className="p-4">
      <PageHeader
        title="Нормализация"
        description="Глобальные правила, справочники и проверка примеров"
        breadcrumbs="Данные / Нормализация"
        actions={
          <div className="flex flex-wrap gap-2">
            <LinkAsButton href="/normalization/rules" variant="outline" data-testid="link-norm-rules">
              Правила
            </LinkAsButton>
            <LinkAsButton href="/normalization/dictionaries" variant="outline" data-testid="link-norm-dictionaries">
              Справочники
            </LinkAsButton>
          </div>
        }
      />
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <LinkAsButton href="/normalization/rules" data-testid="tab-norm-rules">
          Вкладка: правила
        </LinkAsButton>
        <LinkAsButton href="/normalization/dictionaries" variant="outline" data-testid="tab-norm-dicts">
          Вкладка: справочники
        </LinkAsButton>
        <span className="self-center text-muted-foreground">· Тестирование и история — ниже</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-normalization-rules">
        {normalizationRules.map((rule) => (
          <NormalizationRuleCard key={rule.id} rule={rule} />
        ))}
      </div>
      <div className="mt-4 rounded-lg border bg-card p-4" data-testid="normalization-rule-test">
        <h2 className="mb-2 text-lg font-semibold">Тестирование правила</h2>
        <Input placeholder="Введите sample input" data-testid="input-rule-sample" />
        <Button type="button" className="mt-2" data-testid="button-test-rule">
          Проверить
        </Button>
      </div>
      <div className="mt-4 rounded-lg border bg-card p-4 text-sm text-muted-foreground" data-testid="normalization-history-stub">
        <strong className="text-foreground">История изменений</strong> — в MVP отображается как заглушка; события аудита см. раздел «Аудит».
      </div>
    </div>
  );
}
