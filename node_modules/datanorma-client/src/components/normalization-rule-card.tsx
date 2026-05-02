import type { NormalizationRule } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function NormalizationRuleCard({ rule }: { rule: NormalizationRule }) {
  return (
    <Card className="p-4" data-testid={`card-normalization-rule-${rule.id}`}>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-medium">{rule.title}</h3>
        <button data-testid={`toggle-rule-${rule.id}`} className="rounded-md border px-2 py-1 text-xs">
          {rule.enabled ? "Включено" : "Выключено"}
        </button>
      </div>
      <p className="mb-3 text-sm text-muted-foreground">{rule.description}</p>
      <p className="text-xs">Исправлено значений: {rule.fixedCount}</p>
      <p className="mb-3 text-xs">Открыто issues: {rule.issuesCount}</p>
      <Button variant="outline" className="w-full" data-testid={`button-configure-rule-${rule.id}`}>
        Настроить
      </Button>
    </Card>
  );
}
