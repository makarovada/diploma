import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useRoute, useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { DestinationConfigForm } from "@/components/destination-config-form";
import {
  deleteEltDestination,
  fetchEltDestination,
  patchEltDestination,
  postEltDestinationCheck,
} from "@/lib/api-elt";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { formatApiErrorMessage } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import { isNumericEltId } from "@/lib/elt-entity-id";
import {
  parseDestinationConfig,
  destinationConfigToRecord,
  validateDestinationConfig,
  isDestinationConnectorCode,
  type DestinationConfigFormState,
  type DestinationConnectorCode,
} from "@/lib/destination-config";

export function DestinationEditPage() {
  const [, params] = useRoute("/destinations/:destinationId/edit");
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const rawId = params?.destinationId ? decodeURIComponent(params.destinationId) : "";
  const destinationId = isNumericEltId(rawId) ? Number(rawId) : null;

  const [name, setName] = useState("");
  const [connector, setConnector] = useState<DestinationConnectorCode>("postgres");
  const [configState, setConfigState] = useState<DestinationConfigFormState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [checkMsg, setCheckMsg] = useState<string | null>(null);

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey:
      destinationId != null
        ? queryKeys.destinations.eltDetail(destinationId, workspaceCode)
        : ["destinations", "elt", "invalid"],
    queryFn: async () => {
      if (destinationId == null) throw new Error("invalid_id");
      const { item } = await fetchEltDestination(destinationId, workspaceCode);
      return item;
    },
    enabled: destinationId != null,
  });

  useEffect(() => {
    const d = query.data;
    if (!d) return;
    setName(d.name);
    const code = isDestinationConnectorCode(d.connector_code) ? d.connector_code : "postgres";
    setConnector(code);
    setConfigState(parseDestinationConfig(code, d.config ?? {}));
  }, [query.data]);

  const configValidationError = useMemo(
    () => (configState ? validateDestinationConfig(configState) : "Загрузка конфигурации…"),
    [configState],
  );

  const saveMut = useMutation({
    mutationFn: () => {
      if (destinationId == null || !configState) throw new Error("invalid_id");
      if (configValidationError) throw new Error(configValidationError);
      return patchEltDestination(destinationId, {
        workspace_code: workspaceCode,
        name: name.trim() || query.data?.name,
        config: destinationConfigToRecord(configState),
      });
    },
    onSuccess: () => {
      setError(null);
      setSaveMsg("Сохранено");
      void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.destinations.eltDetail(destinationId!, workspaceCode),
      });
    },
    onError: (e: unknown) => {
      setSaveMsg(null);
      setError(formatApiErrorMessage(e, "Ошибка сохранения"));
    },
  });

  const checkMut = useMutation({
    mutationFn: () => {
      if (destinationId == null) throw new Error("invalid_id");
      return postEltDestinationCheck(destinationId, workspaceCode);
    },
    onSuccess: (r) => {
      setCheckMsg(`${r.ok ? "Ок" : "Ошибка"}: ${r.message}`);
    },
    onError: (e: unknown) => {
      setCheckMsg(formatApiErrorMessage(e, "Ошибка проверки"));
    },
  });

  if (!destinationId) {
    return (
      <div className="p-4" data-testid="state-not-found-destination-edit">
        <p>Редактирование доступно только для приёмников ELT с числовым id.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending || wsQuery.isPending || !configState) {
    return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  }
  if (query.isError || !query.data) {
    return (
      <div className="p-4" data-testid="state-not-found-destination-edit">
        <p>Приёмник не найден.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  const dest = query.data;

  return (
    <div className="p-4">
      <PageHeader
        title={`Редактирование: ${dest.name}`}
        description={`Тип: ${dest.connector_code}`}
        breadcrumbs={`Интеграции / Приёмники / ${dest.name} / Изменить`}
        actions={
          <ConfirmDeleteButton
            entityLabel={dest.name}
            testId="button-delete-destination-edit"
            onDelete={() => deleteEltDestination(destinationId, workspaceCode)}
            onSuccess={() => {
              void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
              setLocation("/destinations");
            }}
          />
        }
      />
      <div className="max-w-xl space-y-3" data-testid="form-destination-edit">
        <Input
          placeholder="Название"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="input-destination-edit-name"
        />
        <DestinationConfigForm
          connector={connector}
          value={configState}
          onChange={setConfigState}
          connectorReadOnly
          idPrefix="destination-edit"
        />
        {error ? (
          <p className="text-sm text-destructive" data-testid="error-destination-edit">
            {error}
          </p>
        ) : null}
        {saveMsg ? (
          <p className="text-sm text-muted-foreground" data-testid="text-destination-edit-saved">
            {saveMsg}
          </p>
        ) : null}
        {checkMsg ? (
          <p className="text-sm text-muted-foreground" data-testid="text-destination-edit-check">
            {checkMsg}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending || Boolean(configValidationError)}
            data-testid="button-save-destination-edit"
          >
            Сохранить
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => checkMut.mutate()}
            disabled={checkMut.isPending}
            data-testid="button-check-destination-edit"
          >
            Проверить подключение
          </Button>
          <LinkAsButton
            href={`/destinations/${destinationId}`}
            variant="outline"
            data-testid="button-cancel-destination-edit"
          >
            Отмена
          </LinkAsButton>
        </div>
      </div>
    </div>
  );
}
