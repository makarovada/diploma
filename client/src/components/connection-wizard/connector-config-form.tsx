import { useMemo } from "react";
import {
  GoogleSheetsSourceForm,
  parseGoogleSheetsConfig,
  googleSheetsConfigToRecord,
  emptyGoogleSheetsConfig,
  validateGoogleSheetsConfig,
} from "@/components/google-sheets-source-form";
import { StepSourceCredentials } from "@/components/connection-wizard/step-source-credentials";
import { Button } from "@/components/ui/button";

type Props = {
  connectorCode: string | null;
  configText: string;
  needsPersist: boolean;
  onChangeText: (text: string) => void;
  onSaveConfig: () => void;
  onBeforeGoogleOAuth?: () => void;
  saving: boolean;
  saveError: string | null;
};

export function ConnectorConfigForm({
  connectorCode,
  configText,
  needsPersist,
  onChangeText,
  onSaveConfig,
  onBeforeGoogleOAuth,
  saving,
  saveError,
}: Props) {
  const googleConfig = useMemo(() => {
    try {
      const parsed = JSON.parse(configText || "{}") as Record<string, unknown>;
      return parseGoogleSheetsConfig(parsed);
    } catch {
      return emptyGoogleSheetsConfig();
    }
  }, [configText]);

  if (connectorCode === "google_sheet") {
    return (
      <div className="space-y-3" data-testid="wizard-connector-config-google-sheet">
        <p className="text-sm text-muted-foreground">
          Параметры Google Sheets. После изменений нажмите «Сохранить конфигурацию».
        </p>
        {needsPersist ? (
          <p className="text-sm text-hint" data-testid="hint-credentials-unsaved">
            Сохраните конфигурацию на сервере, чтобы перейти к следующему шагу.
          </p>
        ) : null}
        <GoogleSheetsSourceForm
          idPrefix="wizard-gs"
          value={googleConfig}
          onChange={(cfg) => onChangeText(JSON.stringify(googleSheetsConfigToRecord(cfg), null, 2))}
          onBeforeOAuthRedirect={onBeforeGoogleOAuth}
        />
        {saveError ? (
          <p className="text-sm text-destructive" data-testid="error-save-source-config">
            {saveError}
          </p>
        ) : null}
        <Button
          type="button"
          onClick={onSaveConfig}
          disabled={saving || Boolean(validateGoogleSheetsConfig(googleConfig))}
          data-testid="button-save-source-config"
        >
          {saving ? "Сохранение…" : "Сохранить конфигурацию"}
        </Button>
      </div>
    );
  }

  return (
    <StepSourceCredentials
      configText={configText}
      needsPersist={needsPersist}
      onChangeText={onChangeText}
      onSaveConfig={onSaveConfig}
      saving={saving}
      saveError={saveError}
    />
  );
}
