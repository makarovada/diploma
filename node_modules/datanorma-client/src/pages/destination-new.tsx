import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DestinationConfigForm } from "@/components/destination-config-form";
import { createEltDestination, postEltDestinationCheck } from "@/lib/api-elt";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { formatApiErrorMessage } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import {
  defaultDestinationConfig,
  destinationConfigToRecord,
  validateDestinationConfig,
  type DestinationConfigFormState,
  type DestinationConnectorCode,
} from "@/lib/destination-config";

export function DestinationNewPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [connector, setConnector] = useState<DestinationConnectorCode>("postgres");
  const [configState, setConfigState] = useState<DestinationConfigFormState>(() =>
    defaultDestinationConfig("postgres"),
  );
  const [error, setError] = useState<string | null>(null);
  const [checkMsg, setCheckMsg] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<number | null>(null);

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  useEffect(() => {
    setConfigState(defaultDestinationConfig(connector));
  }, [connector]);

  const configValidationError = useMemo(() => validateDestinationConfig(configState), [configState]);

  const createMut = useMutation({
    mutationFn: () => {
      if (configValidationError) throw new Error(configValidationError);
      return createEltDestination({
        workspace_code: workspaceCode,
        name: name.trim() || "Приёмник",
        connector_code: connector,
        config: destinationConfigToRecord(configState),
      });
    },
    onSuccess: (data) => {
      setError(null);
      setCreatedId(data.item.id);
      void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
    },
    onError: (e: unknown) => {
      setError(formatApiErrorMessage(e, "Ошибка сохранения"));
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
      setCheckMsg(formatApiErrorMessage(e, "Ошибка проверки"));
    },
  });

  return (
    <div className="p-4">
      <PageHeader
        title="Новый приёмник"
        description="PostgreSQL, ClickHouse, CSV или Excel — параметры через форму"
        breadcrumbs="Интеграции / Приёмники / Новый"
      />
      <div className="max-w-xl space-y-3" data-testid="form-new-destination">
        <Input
          placeholder="Название"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="input-destination-name"
        />
        <DestinationConfigForm
          connector={connector}
          value={configState}
          onChange={setConfigState}
          onConnectorChange={setConnector}
          showConnectorSelect
          idPrefix="destination-new"
        />
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
            disabled={createMut.isPending || createdId != null || Boolean(configValidationError)}
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
