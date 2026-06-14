import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { probeRestBuilder } from "@/lib/api-datanorma";
import {
  emptyRestBuilderStream,
  normalizeRestBuilderConfig,
  parseRestBuilderYaml,
  restBuilderConfigToRecord,
  restBuilderConfigToYaml,
  validateRestBuilderConfig,
  type RestBuilderConfig,
  type RestBuilderProbeResult,
  type RestBuilderStream,
} from "@/lib/rest-builder-config";

type Props = {
  value: RestBuilderConfig;
  onChange: (value: RestBuilderConfig) => void;
  idPrefix?: string;
};

type EditorMode = "form" | "yaml";

export function RestBuilderSourceForm({ value, onChange, idPrefix = "rb" }: Props) {
  const [mode, setMode] = useState<EditorMode>("form");
  const [yamlText, setYamlText] = useState(() => restBuilderConfigToYaml(value));
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [probeIndex, setProbeIndex] = useState(0);
  const [probing, setProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<RestBuilderProbeResult | null>(null);
  const [probeError, setProbeError] = useState<string | null>(null);

  const patch = useCallback(
    (partial: Partial<RestBuilderConfig>) => {
      onChange(normalizeRestBuilderConfig({ ...value, ...partial }));
    },
    [onChange, value],
  );

  const patchStream = useCallback(
    (index: number, partial: Partial<RestBuilderStream>) => {
      const streams = value.streams.map((st, i) => (i === index ? { ...st, ...partial } : st));
      onChange(normalizeRestBuilderConfig({ ...value, streams }));
    },
    [onChange, value],
  );

  const addStream = useCallback(() => {
    onChange(normalizeRestBuilderConfig({ ...value, streams: [...value.streams, emptyRestBuilderStream()] }));
  }, [onChange, value]);

  const removeStream = useCallback(
    (index: number) => {
      if (value.streams.length <= 1) return;
      onChange(normalizeRestBuilderConfig({ ...value, streams: value.streams.filter((_, i) => i !== index) }));
    },
    [onChange, value],
  );

  const switchMode = (next: EditorMode) => {
    if (next === mode) return;
    if (next === "yaml") {
      setYamlText(restBuilderConfigToYaml(value));
      setYamlError(null);
    } else {
      try {
        const parsed = parseRestBuilderYaml(yamlText);
        onChange(normalizeRestBuilderConfig(parsed));
        setYamlError(null);
      } catch (e) {
        setYamlError(e instanceof Error ? e.message : "Некорректный YAML");
        return;
      }
    }
    setMode(next);
  };

  const validationError = validateRestBuilderConfig(value);

  const runProbe = async () => {
    setProbing(true);
    setProbeError(null);
    setProbeResult(null);
    try {
      const cfgRecord = restBuilderConfigToRecord(value);
      const result = await probeRestBuilder(cfgRecord, probeIndex);
      setProbeResult(result);
    } catch (e) {
      setProbeError(e instanceof Error ? e.message : "Ошибка проверки запроса");
    } finally {
      setProbing(false);
    }
  };

  return (
    <div className="space-y-4 rounded-lg border bg-card p-4" data-testid="form-rest-builder">
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={mode === "form" ? "default" : "outline"}
          onClick={() => switchMode("form")}
          data-testid="button-rest-builder-mode-form"
        >
          Форма
        </Button>
        <Button
          type="button"
          size="sm"
          variant={mode === "yaml" ? "default" : "outline"}
          onClick={() => switchMode("yaml")}
          data-testid="button-rest-builder-mode-yaml"
        >
          YAML
        </Button>
      </div>

      {mode === "yaml" ? (
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor={`${idPrefix}-yaml`}>
            Connector Builder YAML
          </label>
          <textarea
            id={`${idPrefix}-yaml`}
            className="min-h-[280px] w-full rounded-md border bg-background p-2 font-mono text-sm"
            value={yamlText}
            onChange={(e) => {
              setYamlText(e.target.value);
              setYamlError(null);
              try {
                onChange(normalizeRestBuilderConfig(parseRestBuilderYaml(e.target.value)));
              } catch {
                /* wait for switch to form or save */
              }
            }}
            data-testid="textarea-rest-builder-yaml"
          />
          {yamlError ? (
            <p className="text-sm text-destructive" data-testid="error-rest-builder-yaml">
              {yamlError}
            </p>
          ) : null}
        </div>
      ) : (
        <>
          <div className="space-y-3">
            <p className="text-sm font-medium">Подключение</p>
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-base-url`}>
                Base URL
              </label>
              <Input
                id={`${idPrefix}-base-url`}
                type="url"
                placeholder="https://api.example.com"
                value={value.base_url}
                onChange={(e) => patch({ base_url: e.target.value })}
                data-testid="input-rest-builder-base-url"
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-timeout`}>
                  Таймаут (с)
                </label>
                <Input
                  id={`${idPrefix}-timeout`}
                  type="number"
                  min={1}
                  max={300}
                  value={value.timeout_seconds}
                  onChange={(e) => patch({ timeout_seconds: Number(e.target.value) || 60 })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-openapi`}>
                  OpenAPI URL (опционально)
                </label>
                <Input
                  id={`${idPrefix}-openapi`}
                  type="url"
                  placeholder="https://api.example.com/openapi.json"
                  value={value.openapi_url}
                  onChange={(e) => patch({ openapi_url: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium">Авторизация</p>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-auth-type`}>
                  Метод
                </label>
                <select
                  id={`${idPrefix}-auth-type`}
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={value.auth_type}
                  onChange={(e) =>
                    patch({ auth_type: e.target.value as RestBuilderConfig["auth_type"] })
                  }
                  data-testid="select-rest-builder-auth-type"
                >
                  <option value="none">Без авторизации</option>
                  <option value="bearer">Bearer token</option>
                  <option value="api_key_header">API key в заголовке</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-auth-token`}>
                  Token / API key
                </label>
                <Input
                  id={`${idPrefix}-auth-token`}
                  type="password"
                  autoComplete="off"
                  value={value.auth_token}
                  onChange={(e) => patch({ auth_token: e.target.value })}
                  disabled={value.auth_type === "none"}
                  data-testid="input-rest-builder-auth-token"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-auth-header`}>
                  HTTP заголовок
                </label>
                <Input
                  id={`${idPrefix}-auth-header`}
                  value={value.auth_header_name}
                  onChange={(e) => patch({ auth_header_name: e.target.value })}
                  disabled={value.auth_type === "none"}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground" htmlFor={`${idPrefix}-token-prefix`}>
                  Префикс Bearer
                </label>
                <Input
                  id={`${idPrefix}-token-prefix`}
                  value={value.token_prefix}
                  onChange={(e) => patch({ token_prefix: e.target.value })}
                  disabled={value.auth_type !== "bearer"}
                />
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">Endpoints</p>
              <Button type="button" size="sm" variant="outline" onClick={addStream} data-testid="button-add-endpoint">
                Добавить endpoint
              </Button>
            </div>
            {value.streams.map((st, index) => (
              <Card key={`${st.name}-${index}`} className="space-y-3 p-3" data-testid={`card-endpoint-${index}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">Endpoint {index + 1}</p>
                  {value.streams.length > 1 ? (
                    <Button type="button" size="sm" variant="ghost" onClick={() => removeStream(index)}>
                      Удалить
                    </Button>
                  ) : null}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Имя потока</label>
                    <Input value={st.name} onChange={(e) => patchStream(index, { name: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Path</label>
                    <Input value={st.path} onChange={(e) => patchStream(index, { path: e.target.value })} placeholder="/posts" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Method</label>
                    <select
                      className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={st.method}
                      onChange={(e) => patchStream(index, { method: e.target.value as RestBuilderStream["method"] })}
                    >
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">JSON path до записей</label>
                    <Input
                      value={st.records_json_path}
                      onChange={(e) => patchStream(index, { records_json_path: e.target.value })}
                      placeholder="data.items (пусто — авто)"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Pagination</label>
                    <select
                      className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={st.pagination_type}
                      onChange={(e) =>
                        patchStream(index, {
                          pagination_type: e.target.value as RestBuilderStream["pagination_type"],
                        })
                      }
                    >
                      <option value="none">Нет</option>
                      <option value="offset">Offset</option>
                    </select>
                  </div>
                  {st.pagination_type === "offset" ? (
                    <>
                      <div className="space-y-2">
                        <label className="text-xs text-muted-foreground">limit param</label>
                        <Input value={st.limit_param} onChange={(e) => patchStream(index, { limit_param: e.target.value })} />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs text-muted-foreground">offset param</label>
                        <Input value={st.offset_param} onChange={(e) => patchStream(index, { offset_param: e.target.value })} />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs text-muted-foreground">limit</label>
                        <Input
                          type="number"
                          min={1}
                          value={st.limit}
                          onChange={(e) => patchStream(index, { limit: Number(e.target.value) || 50 })}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs text-muted-foreground">max pages</label>
                        <Input
                          type="number"
                          min={1}
                          value={st.max_pages}
                          onChange={(e) => patchStream(index, { max_pages: Number(e.target.value) || 20 })}
                        />
                      </div>
                    </>
                  ) : null}
                </div>
                {st.method === "POST" ? (
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Body (JSON)</label>
                    <textarea
                      className="min-h-[80px] w-full rounded-md border bg-background p-2 font-mono text-xs"
                      value={st.body_json}
                      onChange={(e) => patchStream(index, { body_json: e.target.value })}
                      placeholder="{}"
                    />
                  </div>
                ) : null}
              </Card>
            ))}
          </div>
        </>
      )}

      {validationError ? (
        <p className="text-sm text-hint" data-testid="hint-rest-builder-validation">
          {validationError}
        </p>
      ) : null}

      <div className="space-y-2 rounded-md border p-3">
        <p className="text-sm font-medium">Проверка запроса</p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground" htmlFor={`${idPrefix}-probe-index`}>
              Endpoint для теста
            </label>
            <select
              id={`${idPrefix}-probe-index`}
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={probeIndex}
              onChange={(e) => setProbeIndex(Number(e.target.value))}
            >
              {value.streams.map((st, i) => (
                <option key={`${st.name}-${i}`} value={i}>
                  {st.name || `endpoint_${i + 1}`}
                </option>
              ))}
            </select>
          </div>
          <Button
            type="button"
            variant="outline"
            disabled={probing || Boolean(validationError)}
            onClick={() => void runProbe()}
            data-testid="button-rest-builder-probe"
          >
            {probing ? "Проверка…" : "Проверить запрос"}
          </Button>
        </div>
        {probeError ? (
          <p className="text-sm text-destructive" data-testid="error-rest-builder-probe">
            {probeError}
          </p>
        ) : null}
        {probeResult ? (
          <div className="space-y-2 text-sm" data-testid="rest-builder-probe-result">
            <p className={probeResult.ok ? "text-green-700 dark:text-green-400" : "text-destructive"}>
              {probeResult.message}
              {probeResult.status_code != null ? ` (HTTP ${probeResult.status_code})` : ""}
            </p>
            <p className="text-muted-foreground">
              Найдено записей: {probeResult.record_count}
              {probeResult.url ? ` · ${probeResult.url}` : ""}
            </p>
            {probeResult.sample_records.length ? (
              <details>
                <summary className="cursor-pointer text-muted-foreground">Sample response</summary>
                <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted p-2 text-xs">
                  {JSON.stringify(probeResult.sample_records, null, 2)}
                </pre>
              </details>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export {
  emptyRestBuilderConfig,
  parseRestBuilderConfig,
  restBuilderConfigToRecord,
  validateRestBuilderConfig,
  type RestBuilderConfig,
} from "@/lib/rest-builder-config";
