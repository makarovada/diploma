import type { WizardFormState } from "@/components/connection-wizard/wizard-types";

type Props = {
  form: WizardFormState;
  sourceLabel: string;
  destinationLabel: string;
  preflightRunning: boolean;
};

export function StepReview({ form, sourceLabel, destinationLabel, preflightRunning }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-review">
      <p className="mb-4 text-sm text-muted-foreground">
        Итоговая конфигурация. На этом шаге выполняется предварительная проверка доступности источника и приёмника.
      </p>
      <ul className="grid gap-2 text-sm" data-testid="wizard-review-summary">
        <li>
          <span className="text-muted-foreground">Название:</span> {form.connectionName || "—"}
        </li>
        <li>
          <span className="text-muted-foreground">Источник:</span> {sourceLabel}
        </li>
        <li>
          <span className="text-muted-foreground">Приёмник:</span> {destinationLabel}
        </li>
        <li>
          <span className="text-muted-foreground">Потоки:</span> {form.enabledStreamNames.join(", ") || "—"}
        </li>
        <li>
          <span className="text-muted-foreground">Нормализация:</span> {form.normalizationEnabled ? "вкл." : "выкл."}
        </li>
        <li>
          <span className="text-muted-foreground">Расписание:</span> {form.scheduleCron.trim() || "ручной запуск"} (
          {form.timezone})
        </li>
      </ul>
      <div className="mt-4 rounded-md border p-3 text-sm" data-testid="wizard-preflight-status">
        {preflightRunning ? (
          <p data-testid="text-preflight-running">Выполняется preflight…</p>
        ) : form.preflightOk === true ? (
          <p className="text-green-700 dark:text-green-400" data-testid="text-preflight-ok">
            Preflight пройден: {form.preflightMessage ?? "источник и приёмник доступны."}
          </p>
        ) : form.preflightOk === false ? (
          <p className="text-destructive" data-testid="text-preflight-fail">
            Preflight не пройден: {form.preflightMessage ?? "ошибка"}
          </p>
        ) : (
          <p className="text-muted-foreground" data-testid="text-preflight-pending">
            Ожидание preflight…
          </p>
        )}
      </div>
    </div>
  );
}
