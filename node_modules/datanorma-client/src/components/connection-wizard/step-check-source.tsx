import { Button } from "@/components/ui/button";
import type { CheckState } from "@/components/connection-wizard/wizard-types";

type Props = {
  check: CheckState;
  checking: boolean;
  onRunCheck: () => void;
  checkError: string | null;
};

export function StepCheckSource({ check, checking, onRunCheck, checkError }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-check-source">
      <p className="mb-3 text-sm text-muted-foreground">
        Проверка выполняется на сервере с текущей сохранённой конфигурацией источника.
      </p>
      <Button type="button" onClick={onRunCheck} disabled={checking} data-testid="button-check-source">
        {checking ? "Проверка…" : "Запустить проверку источника"}
      </Button>
      {checkError ? (
        <p className="mt-3 text-sm text-destructive" data-testid="error-check-source-request">
          {checkError}
        </p>
      ) : null}
      {check ? (
        <div
          className={`mt-4 rounded-md p-3 text-sm ${check.ok ? "surface-ok" : "surface-error"}`}
          data-testid="result-check-source"
        >
          <p className="font-medium" data-testid="text-check-source-status">
            {check.ok ? "Проверка пройдена" : "Проверка не пройдена"}
          </p>
          <p className="mt-1 text-muted-foreground" data-testid="text-check-source-message">
            {check.message}
          </p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="hint-check-source">
          Результат проверки появится здесь.
        </p>
      )}
    </div>
  );
}
