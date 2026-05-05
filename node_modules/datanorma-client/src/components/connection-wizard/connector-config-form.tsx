import { StepSourceCredentials } from "@/components/connection-wizard/step-source-credentials";

type Props = {
  configText: string;
  needsPersist: boolean;
  onChangeText: (text: string) => void;
  onSaveConfig: () => void;
  saving: boolean;
  saveError: string | null;
};

/**
 * Обёртка над UI редактирования конфигурации источника.
 *
 * На следующих итерациях планируется заменить textarea на динамические поля
 * на основании config_schema из catalog'а, но на текущем этапе оставляем
 * совместимый минимальный контур.
 */
export function ConnectorConfigForm({
  configText,
  needsPersist,
  onChangeText,
  onSaveConfig,
  saving,
  saveError,
}: Props) {
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

