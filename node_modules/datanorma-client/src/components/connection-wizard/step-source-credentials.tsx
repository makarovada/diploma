import { Button } from "@/components/ui/button";
import { credentialsJsonError } from "@/components/connection-wizard/wizard-validation";

type Props = {
  configText: string;
  needsPersist: boolean;
  onChangeText: (text: string) => void;
  onSaveConfig: () => void;
  saving: boolean;
  saveError: string | null;
};

export function StepSourceCredentials({
  configText,
  needsPersist,
  onChangeText,
  onSaveConfig,
  saving,
  saveError,
}: Props) {
  const jsonErr = credentialsJsonError(configText);
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-source-credentials">
      <p className="mb-2 text-sm text-muted-foreground">
        Отредактируйте JSON-конфигурацию источника (секреты, пути к файлам, YAML для rest_builder и т.д.). Нажмите
        «Сохранить конфигурацию», затем перейдите к проверке.
      </p>
      {needsPersist ? (
        <p className="mb-2 text-sm text-amber-700 dark:text-amber-400" data-testid="hint-credentials-unsaved">
          Сохраните конфигурацию на сервере, чтобы перейти к следующему шагу.
        </p>
      ) : null}
      <textarea
        className="min-h-[220px] w-full max-w-3xl rounded-md border bg-background p-3 font-mono text-xs"
        value={configText}
        onChange={(e) => onChangeText(e.target.value)}
        spellCheck={false}
        data-testid="textarea-source-config-json"
        aria-invalid={Boolean(jsonErr)}
      />
      {jsonErr ? (
        <p className="mt-1 text-sm text-destructive" data-testid="error-source-config-json">
          {jsonErr}
        </p>
      ) : null}
      {saveError ? (
        <p className="mt-2 text-sm text-destructive" data-testid="error-save-source-config">
          {saveError}
        </p>
      ) : null}
      <Button
        type="button"
        className="mt-3"
        onClick={onSaveConfig}
        disabled={Boolean(jsonErr) || saving}
        data-testid="button-save-source-config"
      >
        {saving ? "Сохранение…" : "Сохранить конфигурацию"}
      </Button>
    </div>
  );
}
