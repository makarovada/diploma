import type { WizardFormState } from "@/components/connection-wizard/wizard-types";
import { describeCronExpression } from "@/lib/schedule-config";
import { describeReplicationPreset, replicationPresetFromFields } from "@/lib/destination-sync-mode";

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
          <span className="text-muted-foreground">Колонок:</span> {form.columnRuleRows.length}
          {form.schemaLayout === "entities" && form.selectedEntities.length > 0 ? (
            <span className="text-muted-foreground">
              {" "}
              (сущности: {form.selectedEntities.map((e) => form.entityLabels[e] ?? e).join(", ")})
            </span>
          ) : null}
        </li>
        <li>
          <span className="text-muted-foreground">Нормализация:</span> {form.normalizationEnabled ? "вкл." : "выкл."}
        </li>
        {form.streamDefaults.length > 0 ? (
          <li>
            <span className="text-muted-foreground">Режимы потоков:</span>
            <ul className="mt-1 list-inside list-disc text-xs">
              {form.streamDefaults.map((s) => (
                <li key={s.stream_name}>
                  <span className="font-mono">{s.stream_name}</span> —{" "}
                  {describeReplicationPreset(
                    replicationPresetFromFields(s.sync_mode, s.destination_sync_mode),
                  )}
                </li>
              ))}
            </ul>
          </li>
        ) : null}
        <li>
          <span className="text-muted-foreground">Расписание:</span>{" "}
          {describeCronExpression(form.scheduleCron, form.timezone)}
          {form.scheduleCron.trim() ? (
            <span className="ml-1 font-mono text-xs text-muted-foreground">({form.scheduleCron.trim()})</span>
          ) : null}
        </li>
      </ul>
      <div className="mt-4 rounded-md border p-3 text-sm" data-testid="wizard-preflight-status">
        {preflightRunning ? (
          <p data-testid="text-preflight-running">Выполняется preflight…</p>
        ) : form.preflightOk === true ? (
          <p className="text-ok" data-testid="text-preflight-ok">
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
