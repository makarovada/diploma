import { Button } from "@/components/ui/button";

type Props = {
  saving: boolean;
  triggering: boolean;
  saveError: string | null;
  doneMessage: string | null;
  onSaveOnly: () => void;
  onSaveAndRun: () => void;
};

export function StepSaveRun({ saving, triggering, saveError, doneMessage, onSaveOnly, onSaveAndRun }: Props) {
  const busy = saving || triggering;
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-save-run">
      <p className="mb-4 text-sm text-muted-foreground">
        Создайте подключение в системе. После сохранения можно сразу запустить синхронизацию (если позволяют права
        доступа).
      </p>
      {saveError ? (
        <p className="mb-3 text-sm text-destructive" data-testid="error-save-connection">
          {saveError}
        </p>
      ) : null}
      {doneMessage ? (
        <p className="mb-3 text-sm text-green-700 dark:text-green-400" data-testid="text-save-success">
          {doneMessage}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" disabled={busy} onClick={onSaveOnly} data-testid="button-save-connection">
          {saving ? "Сохранение…" : "Только сохранить"}
        </Button>
        <Button type="button" disabled={busy} onClick={onSaveAndRun} data-testid="button-save-and-run">
          {triggering ? "Запуск…" : saving ? "Сохранение…" : "Сохранить и запустить"}
        </Button>
      </div>
    </div>
  );
}
