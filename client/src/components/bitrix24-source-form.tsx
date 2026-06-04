import { useCallback } from "react";
import { Input } from "@/components/ui/input";

export type Bitrix24Config = {
  webhook_url: string;
};

export function emptyBitrix24Config(): Bitrix24Config {
  return { webhook_url: "" };
}

/** Базовый URL входящего webhook без /profile.json и лишних слэшей. */
export function normalizeBitrix24WebhookUrl(raw: string): string {
  let url = raw.trim();
  if (!url) return "";
  url = url.replace(/\/profile\.json\/?$/i, "");
  return url.replace(/\/+$/, "");
}

export function parseBitrix24Config(raw: Record<string, unknown>): Bitrix24Config {
  return {
    webhook_url: normalizeBitrix24WebhookUrl(String(raw.webhook_url ?? "")),
  };
}

export function bitrix24ConfigToRecord(cfg: Bitrix24Config): Record<string, unknown> {
  return {
    webhook_url: normalizeBitrix24WebhookUrl(cfg.webhook_url),
  };
}

export function validateBitrix24Config(cfg: Bitrix24Config): string | null {
  const url = normalizeBitrix24WebhookUrl(cfg.webhook_url);
  if (!url) return "Укажите URL входящего webhook Bitrix24.";
  if (!/^https?:\/\//i.test(url)) return "URL webhook должен начинаться с http:// или https://.";
  if (!/\/rest\/\d+\/[a-z0-9]+$/i.test(url)) {
    return "Ожидается URL вида https://portal.bitrix24.ru/rest/1/xxxxxxxx/";
  }
  return null;
}

export function bitrix24WebhookUrlHint(raw: string): string | null {
  if (/\/profile\.json\/?$/i.test(raw.trim())) {
    return "Обнаружен profile.json — при сохранении будет использован базовый URL webhook.";
  }
  return null;
}

type Props = {
  value: Bitrix24Config;
  onChange: (value: Bitrix24Config) => void;
  idPrefix?: string;
};

export function Bitrix24SourceForm({ value, onChange, idPrefix = "bx24" }: Props) {
  const patch = useCallback(
    (partial: Partial<Bitrix24Config>) => {
      onChange({ ...value, ...partial });
    },
    [onChange, value],
  );

  const validationError = validateBitrix24Config(value);
  const profileHint = bitrix24WebhookUrlHint(value.webhook_url);

  return (
    <div className="space-y-4 rounded-lg border bg-card p-4" data-testid="form-bitrix24">
      <div className="space-y-2">
        <label className="text-sm font-medium" htmlFor={`${idPrefix}-webhook-url`}>
          Webhook URL
        </label>
        <Input
          id={`${idPrefix}-webhook-url`}
          type="url"
          placeholder="https://yourcompany.bitrix24.ru/rest/1/xxxxxxxx/"
          value={value.webhook_url}
          onChange={(e) => patch({ webhook_url: e.target.value })}
          data-testid="input-bitrix24-webhook-url"
          autoComplete="off"
        />
        <p className="text-xs text-muted-foreground">
          Bitrix24 → Разработчикам → Входящие вебхуки → скопируйте URL вебхука (права CRM и Задачи на чтение).
          Указывайте базовый адрес,{" "}
          <strong>не</strong> ссылку на <code className="text-xs">profile.json</code>.
        </p>
      </div>

      {profileHint ? (
        <p className="text-sm text-hint" data-testid="hint-bitrix24-profile-url">
          {profileHint}
        </p>
      ) : null}

      {validationError ? (
        <p className="text-sm text-hint" data-testid="hint-bitrix24-validation">
          {validationError}
        </p>
      ) : null}
    </div>
  );
}
