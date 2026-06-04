import { useEffect, useMemo } from "react";
import {
  Bitrix24SourceForm,
  parseBitrix24Config,
  bitrix24ConfigToRecord,
  emptyBitrix24Config,
  validateBitrix24Config,
} from "@/components/bitrix24-source-form";
import {
  GoogleSheetsSourceForm,
  parseGoogleSheetsConfig,
  googleSheetsConfigToRecord,
  emptyGoogleSheetsConfig,
  validateGoogleSheetsConfig,
} from "@/components/google-sheets-source-form";
import { StepSourceCredentials } from "@/components/connection-wizard/step-source-credentials";
import { Button } from "@/components/ui/button";
import { normalizeSourceConfigForConnector } from "@/lib/source-config-normalize";

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

  const bitrix24Config = useMemo(() => {
    try {
      const parsed = JSON.parse(configText || "{}") as Record<string, unknown>;
      return parseBitrix24Config(parsed);
    } catch {
      return emptyBitrix24Config();
    }
  }, [configText]);

  useEffect(() => {
    if (connectorCode !== "bitrix24") return;
    const normalized = JSON.stringify(bitrix24ConfigToRecord(bitrix24Config), null, 2);
    if (normalized !== configText) {
      onChangeText(normalized);
    }
  }, [connectorCode, bitrix24Config, configText, onChangeText]);

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

  if (connectorCode === "bitrix24") {
    return (
      <div className="space-y-3" data-testid="wizard-connector-config-bitrix24">
        <p className="text-sm text-muted-foreground">
          Параметры входящего webhook Bitrix24. После изменений нажмите «Сохранить конфигурацию».
        </p>
        {needsPersist ? (
          <p className="text-sm text-hint" data-testid="hint-credentials-unsaved">
            Сохраните конфигурацию на сервере, чтобы перейти к следующему шагу.
          </p>
        ) : null}
        <Bitrix24SourceForm
          idPrefix="wizard-bx24"
          value={bitrix24Config}
          onChange={(cfg) => onChangeText(JSON.stringify(bitrix24ConfigToRecord(cfg), null, 2))}
        />
        {saveError ? (
          <p className="text-sm text-destructive" data-testid="error-save-source-config">
            {saveError}
          </p>
        ) : null}
        <Button
          type="button"
          onClick={onSaveConfig}
          disabled={saving || Boolean(validateBitrix24Config(bitrix24Config))}
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
