import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createEltDestination, postEltDestinationCheck } from "@/lib/api-elt";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { ApiError } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";

const CONNECTORS = [
  { value: "postgres", label: "PostgreSQL" },
  { value: "csv", label: "CSV (файл)" },
  { value: "xlsx", label: "Excel (.xlsx)" },
  { value: "clickhouse", label: "ClickHouse (HTTP)" },
] as const;

export function DestinationNewPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [connector, setConnector] = useState<string>("postgres");
  const [configText, setConfigText] = useState("{}");
  const [error, setError] = useState<string | null>(null);
  const [checkMsg, setCheckMsg] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<number | null>(null);

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const createMut = useMutation({
    mutationFn: () => {
      let config: Record<string, unknown> = {};
      try {
        config = JSON.parse(configText || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("Некорректный JSON в конфигурации");
      }
      return createEltDestination({
        workspace_code: workspaceCode,
        name: name.trim() || "Приёмник",
        connector_code: connector,
        config,
      });
    },
    onSuccess: (data) => {
      setError(null);
      setCreatedId(data.item.id);
      void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError) setError(e.message);
      else if (e instanceof Error) setError(e.message);
      else setError("Ошибка сохранения");
    },
  });

  const checkMut = useMutation({
    mutationFn: async () => {
      if (!createdId) {
        throw new Error("Сначала сохраните приёмник, затем нажмите «Проверить».");
      }
      return postEltDestinationCheck(createdId, workspaceCode);
    },
    onSuccess: (r) => {
      setCheckMsg(`${r.ok ? "Ок" : "Ошибка"}: ${r.message}`);
    },
    onError: (e: unknown) => {
      setCheckMsg(e instanceof Error ? e.message : "Ошибка проверки");
    },
  });

  return (
    <div className="p-4">
      <PageHeader
        title="Новый приёмник"
        description="PostgreSQL, ClickHouse, CSV или XLSX — конфигурация в JSON"
        breadcrumbs="Интеграции / Приёмники / Новый"
      />
      <div className="max-w-xl space-y-3" data-testid="form-new-destination">
        <Input
          placeholder="Название"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="input-destination-name"
        />
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="select-destination-connector">
            Тип приёмника
          </label>
          <select
            id="select-destination-connector"
            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
            value={connector}
            onChange={(e) => setConnector(e.target.value)}
            data-testid="select-destination-connector"
          >
            {CONNECTORS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted-foreground" htmlFor="textarea-destination-config">
            Config (JSON): для postgres — url, schema, table; csv/xlsx — path; clickhouse — host, port, database,
            table, user, password
          </label>
          <textarea
            id="textarea-destination-config"
            className="min-h-[140px] w-full rounded-md border bg-background p-2 font-mono text-sm"
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
            data-testid="textarea-destination-config"
          />
        </div>
        {error ? (
          <p className="text-sm text-destructive" data-testid="error-destination-save">
            {error}
          </p>
        ) : null}
        {checkMsg ? (
          <p className="text-sm text-muted-foreground" data-testid="text-destination-check-result">
            {checkMsg}
          </p>
        ) : null}
        {createdId ? (
          <p className="text-sm text-muted-foreground" data-testid="text-destination-created-id">
            Создан приёмник #{createdId}.{" "}
            <button
              type="button"
              className="text-primary underline"
              onClick={() => setLocation(`/destinations/${encodeURIComponent(String(createdId))}`)}
              data-testid="link-open-created-destination"
            >
              Открыть карточку
            </button>
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() => createMut.mutate()}
            disabled={createMut.isPending || createdId != null}
            data-testid="button-save-destination"
          >
            Сохранить
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => checkMut.mutate()}
            disabled={checkMut.isPending || !createdId}
            data-testid="button-check-destination-new"
          >
            Проверить подключение
          </Button>
          <LinkAsButton href="/destinations" variant="outline" data-testid="button-cancel-destination">
            Отмена
          </LinkAsButton>
        </div>
      </div>
    </div>
  );
}
