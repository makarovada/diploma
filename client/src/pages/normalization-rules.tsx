import { PageHeader } from "@/components/page-header";
import { NormalizationRuleCard } from "@/components/normalization-rule-card";
import { normalizationRules } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";

export function NormalizationRulesPage() {
  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Правила нормализации"
        description="Глобальные группы правил"
        breadcrumbs="Данные / Нормализация / Правила"
        actions={<LinkAsButton href="/normalization/dictionaries" variant="outline" data-testid="link-to-norm-dictionaries">Справочники</LinkAsButton>}
      />
      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-normalization-rules-page">
        {normalizationRules.map((r) => (
          <NormalizationRuleCard key={r.id} rule={r} />
        ))}
      </div>
    </div>
  );
}
