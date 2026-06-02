import { Button } from "@/components/ui/button";
import type { CheckState } from "@/components/connection-wizard/wizard-types";

type Props = {
  check: CheckState;
  checking: boolean;
  onRunCheck: () => void;
  checkError: string | null;
};

export function StepCheckDestination({ check, checking, onRunCheck, checkError }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-check-destination">
      <p className="mb-3 text-sm text-muted-foreground">
        Проверка приёмника выполняется на сервере (например ping PostgreSQL для warehouse).
      </p>
      <Button type="button" onClick={onRunCheck} disabled={checking} data-testid="button-check-destination">
        {checking ? "Проверка…" : "Запустить проверку приёмника"}
      </Button>
      {checkError ? (
        <p className="mt-3 text-sm text-destructive" data-testid="error-check-destination-request">
          {checkError}
        </p>
      ) : null}
      {check ? (
        <div
          className={`mt-4 rounded-md p-3 text-sm ${check.ok ? "surface-ok" : "surface-error"}`}
          data-testid="result-check-destination"
        >
          <p className="font-medium" data-testid="text-check-destination-status">
            {check.ok ? "Проверка пройдена" : "Проверка не пройдена"}
          </p>
          <p className="mt-1 text-muted-foreground" data-testid="text-check-destination-message">
            {check.message}
          </p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="hint-check-destination">
          Результат проверки появится здесь.
        </p>
      )}
    </div>
  );
}
