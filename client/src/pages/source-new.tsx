import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  emptyGoogleSheetsConfig,
  GoogleSheetsSourceForm,
  googleSheetsConfigToRecord,
  validateGoogleSheetsConfig,
  type GoogleSheetsConfig,
} from "@/components/google-sheets-source-form";
import {
  emptyBitrix24Config,
  Bitrix24SourceForm,
  bitrix24ConfigToRecord,
  parseBitrix24Config,
  validateBitrix24Config,
  type Bitrix24Config,
} from "@/components/bitrix24-source-form";
import {
  emptyRestBuilderConfig,
  RestBuilderSourceForm,
  restBuilderConfigToRecord,
  validateRestBuilderConfig,
  type RestBuilderConfig,
} from "@/components/rest-builder-source-form";
import { hasGoogleOAuthCallback, OAUTH_WIZARD_RESTORE_KEY } from "@/lib/oauth-return";
import { fetchV1ConnectorsCatalog, fetchWorkspaces } from "@/lib/api-datanorma";
import { createEltSource } from "@/lib/api-elt";
import { ApiError } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";

type CatalogItem = {
  code?: string;
  name?: string;
  category?: string;
  config_schema?: Record<string, unknown>;
};

function connectorConfigHint(connectorCode: string | null): string {
  if (connectorCode === "google_sheet") {
    return "Google Sheets: ID таблицы и вход через Google OAuth.";
  }
  if (connectorCode === "bitrix24") {
    return "Bitrix24: URL входящего webhook (CRM и задачи на чтение).";
  }
  if (connectorCode === "yandex_metrika") {
    return "Для Яндекс Метрики: oauth_token, counter_id.";
  }
  if (connectorCode === "rest_builder") {
    return "REST API Builder: base URL, авторизация, endpoints. Можно переключиться на YAML.";
  }
  return "Config (JSON) коннектора.";
}

function defaultConfigFromSchema(schema: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!schema || typeof schema !== "object") return {};
  const props = (schema.properties as Record<string, Record<string, unknown>>) || {};
  const required = (schema.required as string[]) || [];
  const out: Record<string, unknown> = {};
  for (const k of required) {
    const p = props[k];
    const def = p?.default;
    out[k] = def !== undefined ? def : "";
  }
  for (const k of Object.keys(props)) {
    if (k in out) continue;
    const p = props[k];
    if (p && typeof p === "object" && "default" in p && p.default !== undefined) {
      out[k] = p.default as unknown;
    }
  }
  return out;
}

export function SourceNewPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [pickedCode, setPickedCode] = useState<string | null>(null);
  const [configText, setConfigText] = useState("{}");
  const [googleSheetsConfig, setGoogleSheetsConfig] = useState<GoogleSheetsConfig>(emptyGoogleSheetsConfig);
  const [bitrix24Config, setBitrix24Config] = useState<Bitrix24Config>(emptyBitrix24Config);
  const [restBuilderConfig, setRestBuilderConfig] = useState<RestBuilderConfig>(emptyRestBuilderConfig);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hasGoogleOAuthCallback()) return;
    try {
      const raw = sessionStorage.getItem(`${OAUTH_WIZARD_RESTORE_KEY}_source_new`);
      if (!raw) return;
      const saved = JSON.parse(raw) as {
        name?: string;
        googleSheetsConfig?: GoogleSheetsConfig;
      };
      sessionStorage.removeItem(`${OAUTH_WIZARD_RESTORE_KEY}_source_new`);
      if (saved.name) setName(saved.name);
      if (saved.googleSheetsConfig) setGoogleSheetsConfig(saved.googleSheetsConfig);
    } catch {
      /* ignore */
    }
  }, []);

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const catalogQuery = useQuery({
    queryKey: ["connectors-catalog", "source-new"],
    queryFn: async () => {
      const body = await fetchV1ConnectorsCatalog("source");
      return Array.isArray(body.items) ? (body.items as CatalogItem[]) : [];
    },
  });
  const connectorsCatalog = catalogQuery.data ?? [];

  const picked = useMemo(
    () => (pickedCode ? connectorsCatalog.find((c) => String(c.code) === pickedCode) : null),
    [connectorsCatalog, pickedCode],
  );

  const applySchemaTemplate = useCallback(
    (item: CatalogItem | null) => {
      const schema = item?.config_schema;
      const tmpl = defaultConfigFromSchema(schema);
      setConfigText(JSON.stringify(Object.keys(tmpl).length ? tmpl : {}, null, 2));
      if (String(item?.code) === "google_sheet") {
        setGoogleSheetsConfig(emptyGoogleSheetsConfig());
      }
      if (String(item?.code) === "bitrix24") {
        setBitrix24Config(parseBitrix24Config(tmpl));
      }
      if (String(item?.code) === "rest_builder") {
        setRestBuilderConfig(emptyRestBuilderConfig());
      }
    },
    [],
  );

  const buildConfig = useCallback((): Record<string, unknown> => {
    if (pickedCode === "google_sheet") {
      return googleSheetsConfigToRecord(googleSheetsConfig);
    }
    if (pickedCode === "bitrix24") {
      return bitrix24ConfigToRecord(bitrix24Config);
    }
    if (pickedCode === "rest_builder") {
      return restBuilderConfigToRecord(restBuilderConfig);
    }
    return JSON.parse(configText || "{}") as Record<string, unknown>;
  }, [pickedCode, googleSheetsConfig, bitrix24Config, restBuilderConfig, configText]);

  const configValidationError = useMemo(() => {
    if (pickedCode === "google_sheet") {
      return validateGoogleSheetsConfig(googleSheetsConfig);
    }
    if (pickedCode === "bitrix24") {
      return validateBitrix24Config(bitrix24Config);
    }
    if (pickedCode === "rest_builder") {
      return validateRestBuilderConfig(restBuilderConfig);
    }
    try {
      JSON.parse(configText || "{}");
      return null;
    } catch {
      return "Некорректный JSON в конфигурации";
    }
  }, [pickedCode, googleSheetsConfig, bitrix24Config, restBuilderConfig, configText]);

  const createMut = useMutation({
    mutationFn: () => {
      if (!pickedCode?.trim()) throw new Error("Выберите коннектор");
      if (configValidationError) throw new Error(configValidationError);
      return createEltSource({
        workspace_code: workspaceCode,
        name: name.trim() || picked?.name || pickedCode,
        connector_code: pickedCode.trim(),
        config: buildConfig(),
      });
    },
    onSuccess: (data) => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["sources", "elt"] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sources.list() });
      setLocation(`/connections/new?source=${encodeURIComponent(String(data.item.id))}`);
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError) setError(e.message);
      else if (e instanceof Error) setError(e.message);
      else setError("Ошибка сохранения");
    },
  });

  return (
    <div className="p-4">
      <PageHeader
        title="Новый источник"
        description="Выберите коннектор и задайте параметры доступа. После сохранения откроется мастер подключения."
        breadcrumbs="Интеграции / Источники / Новый"
      />
      <div className="mb-4 max-w-xl space-y-2">
        <Input
          placeholder="Название источника"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="input-source-name"
        />
      </div>
      <p className="mb-2 text-sm font-medium">Коннекторы</p>
      {catalogQuery.isPending ? (
        <p className="text-sm text-muted-foreground">Загрузка каталога…</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="grid-source-connectors">
          {connectorsCatalog.map((c) => {
            const code = String(c.code ?? "");
            const selected = pickedCode === code;
            return (
              <Card key={code || `idx-${String(c.name)}`} className={`p-4 ${selected ? "ring-2 ring-primary" : ""}`} data-testid={`card-connector-pick-${code}`}>
                <p className="font-medium">{String(c.name ?? c.code)}</p>
                <p className="text-xs text-muted-foreground">{String(c.category ?? "source")}</p>
                <Button
                  className="mt-2 w-full"
                  variant={selected ? "default" : "outline"}
                  type="button"
                  data-testid={`button-select-connector-${code}`}
                  onClick={() => {
                    setPickedCode(code);
                    applySchemaTemplate(c);
                  }}
                >
                  {selected ? "Выбрано" : "Выбрать"}
                </Button>
              </Card>
            );
          })}
        </div>
      )}
      {pickedCode ? (
        <div className="mt-6 max-w-3xl space-y-2">
          <p className="text-sm text-muted-foreground">{connectorConfigHint(pickedCode)}</p>
          {pickedCode === "google_sheet" ? (
            <GoogleSheetsSourceForm
              value={googleSheetsConfig}
              onChange={setGoogleSheetsConfig}
              idPrefix="source-new"
              onBeforeOAuthRedirect={() => {
                sessionStorage.setItem(
                  `${OAUTH_WIZARD_RESTORE_KEY}_source_new`,
                  JSON.stringify({ name, googleSheetsConfig }),
                );
              }}
            />
          ) : pickedCode === "bitrix24" ? (
            <Bitrix24SourceForm value={bitrix24Config} onChange={setBitrix24Config} idPrefix="source-new-bx24" />
          ) : pickedCode === "rest_builder" ? (
            <RestBuilderSourceForm value={restBuilderConfig} onChange={setRestBuilderConfig} idPrefix="source-new-rb" />
          ) : (
            <>
              <label className="text-sm text-muted-foreground" htmlFor="source-config-json">
                Параметры (JSON)
              </label>
              <textarea
                id="source-config-json"
                className="min-h-[160px] w-full rounded-md border bg-background p-2 font-mono text-sm"
                value={configText}
                onChange={(e) => setConfigText(e.target.value)}
                data-testid="textarea-source-config"
              />
              <Button type="button" variant="outline" onClick={() => applySchemaTemplate(picked ?? null)}>
                Подставить шаблон из схемы
              </Button>
            </>
          )}
        </div>
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-destructive" data-testid="error-source-save">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          disabled={!pickedCode || createMut.isPending || Boolean(configValidationError)}
          onClick={() => createMut.mutate()}
          data-testid="button-save-source"
        >
          Сохранить и перейти к подключению
        </Button>
        <LinkAsButton href="/sources" variant="outline" data-testid="button-cancel-source">
          Отмена
        </LinkAsButton>
      </div>
    </div>
  );
}
