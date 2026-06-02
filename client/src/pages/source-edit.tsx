import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRoute, useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  GoogleSheetsSourceForm,
  parseGoogleSheetsConfig,
  googleSheetsConfigToRecord,
  validateGoogleSheetsConfig,
  type GoogleSheetsConfig,
} from "@/components/google-sheets-source-form";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { fetchEltSource, patchEltSource, deleteEltSource } from "@/lib/api-elt";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { formatApiErrorMessage } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";

export function SourceEditPage() {
  const [, params] = useRoute("/sources/:sourceId/edit");
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const rawId = params?.sourceId ? decodeURIComponent(params.sourceId) : "";
  const sourceId = /^\d+$/.test(rawId) ? Number(rawId) : null;

  const [name, setName] = useState("");
  const [configText, setConfigText] = useState("{}");
  const [googleSheetsConfig, setGoogleSheetsConfig] = useState<GoogleSheetsConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey: sourceId != null ? queryKeys.sources.eltDetail(sourceId, workspaceCode) : ["sources", "elt", "invalid"],
    queryFn: async () => {
      if (sourceId == null) throw new Error("invalid_id");
      const { item } = await fetchEltSource(sourceId, workspaceCode);
      return item;
    },
    enabled: sourceId != null,
  });

  useEffect(() => {
    const s = query.data;
    if (!s) return;
    setName(s.name);
    if (s.connector_code === "google_sheet") {
      setGoogleSheetsConfig(parseGoogleSheetsConfig(s.config ?? {}));
    } else {
      setConfigText(JSON.stringify(s.config ?? {}, null, 2));
      setGoogleSheetsConfig(null);
    }
  }, [query.data]);

  const connectorCode = query.data?.connector_code ?? "";

  const buildConfig = useCallback((): Record<string, unknown> => {
    if (connectorCode === "google_sheet" && googleSheetsConfig) {
      return googleSheetsConfigToRecord(googleSheetsConfig);
    }
    return JSON.parse(configText || "{}") as Record<string, unknown>;
  }, [connectorCode, googleSheetsConfig, configText]);

  const configValidationError = useMemo(() => {
    if (connectorCode === "google_sheet" && googleSheetsConfig) {
      return validateGoogleSheetsConfig(googleSheetsConfig);
    }
    try {
      JSON.parse(configText || "{}");
      return null;
    } catch {
      return "Некорректный JSON в конфигурации";
    }
  }, [connectorCode, googleSheetsConfig, configText]);

  const saveMut = useMutation({
    mutationFn: () => {
      if (sourceId == null) throw new Error("invalid_id");
      if (configValidationError) throw new Error(configValidationError);
      return patchEltSource(sourceId, {
        workspace_code: workspaceCode,
        name: name.trim() || query.data?.name,
        config: buildConfig(),
      });
    },
    onSuccess: () => {
      setError(null);
      setSaveMsg("Сохранено");
      void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltList(workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltDetail(sourceId!, workspaceCode) });
    },
    onError: (e: unknown) => {
      setSaveMsg(null);
      setError(formatApiErrorMessage(e, "Ошибка сохранения"));
    },
  });

  if (!sourceId) {
    return (
      <div className="p-4" data-testid="state-not-found-source-edit">
        <p>Редактирование доступно только для источников с числовым id.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending || wsQuery.isPending) {
    return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  }
  if (query.isError || !query.data) {
    return (
      <div className="p-4" data-testid="state-not-found-source-edit">
        <p>Источник не найден.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  return (
    <div className="p-4">
      <PageHeader
        title={`Редактирование: ${query.data.name}`}
        description={`Коннектор: ${connectorCode} (не меняется)`}
        breadcrumbs={`Интеграции / Источники / ${query.data.name} / Изменить`}
        actions={
          <ConfirmDeleteButton
            entityLabel={query.data.name}
            testId="button-delete-source-edit"
            onDelete={() => deleteEltSource(sourceId, workspaceCode)}
            onSuccess={() => {
              void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltList(workspaceCode) });
              setLocation("/sources");
            }}
          />
        }
      />
      <div className="mb-4 max-w-xl space-y-3" data-testid="form-source-edit">
        <Input
          placeholder="Название источника"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="input-source-edit-name"
        />
        {connectorCode === "google_sheet" && googleSheetsConfig ? (
          <GoogleSheetsSourceForm
            value={googleSheetsConfig}
            onChange={setGoogleSheetsConfig}
            idPrefix="source-edit"
          />
        ) : (
          <>
            <label className="text-sm text-muted-foreground" htmlFor="source-edit-config-json">
              Параметры (JSON)
            </label>
            <textarea
              id="source-edit-config-json"
              className="min-h-[200px] w-full rounded-md border bg-background p-2 font-mono text-sm"
              value={configText}
              onChange={(e) => setConfigText(e.target.value)}
              data-testid="textarea-source-edit-config"
            />
          </>
        )}
        {error ? (
          <p className="text-sm text-destructive" data-testid="error-source-edit">
            {error}
          </p>
        ) : null}
        {saveMsg ? (
          <p className="text-sm text-muted-foreground" data-testid="text-source-edit-saved">
            {saveMsg}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={saveMut.isPending || Boolean(configValidationError)}
            onClick={() => saveMut.mutate()}
            data-testid="button-save-source-edit"
          >
            Сохранить
          </Button>
          <LinkAsButton href={`/sources/${sourceId}`} variant="outline" data-testid="button-cancel-source-edit">
            Отмена
          </LinkAsButton>
        </div>
      </div>
      <Card className="mt-4 max-w-xl p-4 text-sm text-muted-foreground">
        После сохранения параметров можно создать или обновить подключение в мастере.
        <LinkAsButton
          href={`/connections/new?source=${encodeURIComponent(String(sourceId))}`}
          className="ml-2"
          data-testid="button-wizard-from-source-edit"
        >
          Мастер подключения
        </LinkAsButton>
      </Card>
    </div>
  );
}
