import { NormalizationRuleCard } from "@/components/normalization-rule-card";
import type { NormalizationRule } from "@/lib/types";

const normalizationRules: NormalizationRule[] = [
  { id: "rule-date", title: "Даты и время", enabled: true, fixedCount: 0, issuesCount: 0, description: "Разбор дат/времени." },
  { id: "rule-phone", title: "Телефоны", enabled: true, fixedCount: 0, issuesCount: 0, description: "Нормализация E.164." },
  { id: "rule-email", title: "Email", enabled: true, fixedCount: 0, issuesCount: 0, description: "trim/lowercase." },
  { id: "rule-inn", title: "ИНН / КПП", enabled: true, fixedCount: 0, issuesCount: 0, description: "Проверка формата." },
];

type Props = {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
};

export function StepNormalization({ enabled, onToggle }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-normalization">
      <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
          data-testid="checkbox-normalization-enabled"
        />
        Включить этап нормализации в пайплайне для этого подключения
      </label>
      <p className="mt-2 text-xs text-muted-foreground">
        Флаг сохраняется вместе с подключением (метаданные мастера). Детальные правила настраиваются в разделе
        «Нормализация».
      </p>
      <p className="mb-2 mt-6 text-sm font-medium">Справочно: активные правила качества</p>
      <div className="grid gap-3 md:grid-cols-2" data-testid="wizard-normalization-rule-cards">
        {normalizationRules.slice(0, 4).map((rule) => (
          <NormalizationRuleCard key={rule.id} rule={rule} />
        ))}
      </div>
    </div>
  );
}
