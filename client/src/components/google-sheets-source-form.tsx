import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchGoogleOAuthComplete, fetchGoogleOAuthStart } from "@/lib/api-google-oauth";
import { ApiError } from "@/lib/api-client";
import {
  buildOAuthReturnUrl,
  isGoogleOAuthStateAlreadyCompleted,
  markGoogleOAuthStateCompleted,
  readGoogleOAuthCallbackParams,
  stripGoogleOAuthParamsFromLocation,
  takePendingGoogleOAuthError,
  takePendingGoogleOAuthState,
} from "@/lib/oauth-return";

const DRAFT_STORAGE_KEY = "datanorma_google_sheets_draft";

export type GoogleSheetsConfig = {
  spreadsheet_id: string;
  worksheet: string;
  oauth_refresh_token?: string;
  oauth_access_token?: string;
};

export function emptyGoogleSheetsConfig(): GoogleSheetsConfig {
  return { spreadsheet_id: "", worksheet: "0" };
}

export function parseGoogleSheetsConfig(raw: Record<string, unknown>): GoogleSheetsConfig {
  return {
    spreadsheet_id: String(raw.spreadsheet_id ?? ""),
    worksheet: String(raw.worksheet ?? "0") || "0",
    oauth_refresh_token: raw.oauth_refresh_token ? String(raw.oauth_refresh_token) : undefined,
    oauth_access_token: raw.oauth_access_token ? String(raw.oauth_access_token) : undefined,
  };
}

export function googleSheetsConfigToRecord(cfg: GoogleSheetsConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {
    spreadsheet_id: cfg.spreadsheet_id.trim(),
    worksheet: cfg.worksheet.trim() || "0",
  };
  if (cfg.oauth_refresh_token?.trim()) {
    out.oauth_refresh_token = cfg.oauth_refresh_token.trim();
  }
  if (cfg.oauth_access_token?.trim()) {
    out.oauth_access_token = cfg.oauth_access_token.trim();
  }
  return out;
}

type Props = {
  value: GoogleSheetsConfig;
  onChange: (value: GoogleSheetsConfig) => void;
  idPrefix?: string;
  /** Сохранить черновик страницы (мастер подключения и т.д.) перед уходом на Google */
  onBeforeOAuthRedirect?: () => void;
};

export function GoogleSheetsSourceForm({ value, onChange, idPrefix = "gs", onBeforeOAuthRedirect }: Props) {
  const [oauthBusy, setOauthBusy] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [oauthDone, setOauthDone] = useState(Boolean(value.oauth_refresh_token?.trim()));

  const patch = useCallback(
    (partial: Partial<GoogleSheetsConfig>) => {
      onChange({ ...value, ...partial });
    },
    [onChange, value],
  );

  useEffect(() => {
    setOauthDone(Boolean(value.oauth_refresh_token?.trim()));
  }, [value.oauth_refresh_token]);

  useEffect(() => {
    const urlParams = readGoogleOAuthCallbackParams();
    const state = urlParams.state || takePendingGoogleOAuthState();
    const error = urlParams.error || takePendingGoogleOAuthError();
    if (!state && !error) return;

    if (error) {
      setOauthError(`Google OAuth: ${error}`);
      stripGoogleOAuthParamsFromLocation();
      return;
    }

    if (!state) return;
    if (isGoogleOAuthStateAlreadyCompleted(state)) {
      stripGoogleOAuthParamsFromLocation();
      return;
    }

    setOauthBusy(true);
    setOauthError(null);
    fetchGoogleOAuthComplete(state)
      .then((tokens) => {
        markGoogleOAuthStateCompleted(state);
        let draft = emptyGoogleSheetsConfig();
        try {
          const raw = sessionStorage.getItem(DRAFT_STORAGE_KEY);
          if (raw) draft = { ...draft, ...(JSON.parse(raw) as GoogleSheetsConfig) };
        } catch {
          /* ignore */
        } finally {
          sessionStorage.removeItem(DRAFT_STORAGE_KEY);
        }
        onChange({
          ...draft,
          oauth_refresh_token: tokens.oauth_refresh_token,
          oauth_access_token: tokens.oauth_access_token ?? undefined,
        });
        setOauthDone(true);
        setOauthError(null);
        stripGoogleOAuthParamsFromLocation();
      })
      .catch((e: unknown) => {
        let msg = e instanceof Error ? e.message : "Ошибка OAuth";
        if (e instanceof ApiError) {
          msg = e.message;
          try {
            const j = JSON.parse(e.body) as { detail?: { message?: string; error_code?: string } | string };
            const d = j.detail;
            if (typeof d === "object" && d?.message) msg = d.message;
            else if (typeof d === "string") msg = d;
            else if (e.status === 404) {
              msg = "Сессия Google OAuth истекла. Нажмите «Подключить Google» ещё раз.";
            }
          } catch {
            if (e.status === 404) {
              msg = "Сессия Google OAuth истекла. Нажмите «Подключить Google» ещё раз.";
            }
          }
        }
        setOauthError(
          e instanceof ApiError && e.status === 401
            ? `${msg}. Войдите в DataNorma снова и повторите «Подключить Google».`
            : msg,
        );
        stripGoogleOAuthParamsFromLocation();
      })
      .finally(() => setOauthBusy(false));
  }, [onChange]);

  const onConnectGoogle = async () => {
    setOauthBusy(true);
    setOauthError(null);
    try {
      sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(value));
      onBeforeOAuthRedirect?.();
      const { authorization_url } = await fetchGoogleOAuthStart(buildOAuthReturnUrl());
      window.location.href = authorization_url;
    } catch (e: unknown) {
      setOauthError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Не удалось начать OAuth");
      setOauthBusy(false);
    }
  };

  const validationError =
    !value.spreadsheet_id.trim()
      ? "Укажите ID таблицы (фрагмент URL между /d/ и /edit)."
      : !value.oauth_refresh_token?.trim()
        ? "Подключите аккаунт Google (кнопка ниже)."
        : null;

  return (
    <div className="space-y-4 rounded-lg border bg-card p-4" data-testid="form-google-sheets">
      <div className="space-y-2">
        <label className="text-sm font-medium" htmlFor={`${idPrefix}-spreadsheet-id`}>
          ID таблицы Google Sheets
        </label>
        <Input
          id={`${idPrefix}-spreadsheet-id`}
          placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
          value={value.spreadsheet_id}
          onChange={(e) => patch({ spreadsheet_id: e.target.value })}
          data-testid="input-spreadsheet-id"
        />
        <p className="text-xs text-muted-foreground">
          Из URL: https://docs.google.com/spreadsheets/d/<strong>ЭТОТ_ID</strong>/edit
        </p>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium" htmlFor={`${idPrefix}-worksheet`}>
          Лист
        </label>
        <Input
          id={`${idPrefix}-worksheet`}
          placeholder="0"
          value={value.worksheet}
          onChange={(e) => patch({ worksheet: e.target.value })}
          data-testid="input-worksheet"
        />
        <p className="text-xs text-muted-foreground">Номер вкладки (0 — первая) или имя листа, например orders</p>
      </div>

      <div className="space-y-2 rounded-md border border-dashed p-3">
        <p className="text-sm font-medium">Доступ Google</p>
        <p className="text-xs text-muted-foreground">
          Войдите через Google и разрешите чтение таблиц. Таблица должна быть доступна вашему Google-аккаунту.
        </p>
        {oauthDone ? (
          <p className="text-sm text-ok" data-testid="text-google-oauth-connected">
            Google подключён
          </p>
        ) : (
          <p className="text-sm text-muted-foreground" data-testid="text-google-oauth-not-connected">
            Google не подключён
          </p>
        )}
        <Button
          type="button"
          variant="outline"
          disabled={oauthBusy}
          onClick={() => void onConnectGoogle()}
          data-testid="button-google-oauth-connect"
        >
          {oauthBusy ? "Подключение…" : oauthDone ? "Переподключить Google" : "Подключить Google"}
        </Button>
        {oauthError ? (
          <p className="text-sm text-destructive" data-testid="error-google-oauth">
            {oauthError}
          </p>
        ) : null}
      </div>

      {validationError ? (
        <p className="text-sm text-hint" data-testid="hint-google-sheets-validation">
          {validationError}
        </p>
      ) : null}
    </div>
  );
}

export function validateGoogleSheetsConfig(cfg: GoogleSheetsConfig): string | null {
  if (!cfg.spreadsheet_id.trim()) return "Укажите spreadsheet_id.";
  if (!cfg.oauth_refresh_token?.trim()) return "Подключите Google OAuth.";
  return null;
}
