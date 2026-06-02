import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRoute, useLocation } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { fetchDestinationsCatalog, fetchWorkspaces, mapDestinationCatalogItem } from "@/lib/api-datanorma";
import {
  deleteEltDestination,
  fetchEltDestination,
  postEltDestinationCheck,
} from "@/lib/api-elt";
import { queryKeys } from "@/lib/query-keys";
import { isNumericEltId } from "@/lib/elt-entity-id";
import type { Destination } from "@/lib/types";
import { formatApiErrorMessage } from "@/lib/api-client";
import {
  describeDestinationConfig,
  isDestinationConnectorCode,
  parseDestinationConfig,
} from "@/lib/destination-config";
import { ResourceAccessPanel } from "@/components/resource-access-panel";
import { useAuth } from "@/app/auth-context";
import { usePermission } from "@/hooks/use-permission";

async function loadDestinationCatalogById(id: string, workspaceCode: string): Promise<Destination> {
  const { items } = await fetchDestinationsCatalog(undefined, workspaceCode);
  const row = items.find((x) => x.id === id);
  if (row) return mapDestinationCatalogItem(row);
  throw new Error("not_found");
}

export function DestinationDetailPage() {
  const [, params] = useRoute("/destinations/:destinationId");
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManageAccess = Boolean(user?.is_workspace_admin) || usePermission("destination.delete");
  const destinationId = params?.destinationId ? decodeURIComponent(params.destinationId) : "";
  const numericId = isNumericEltId(destinationId) ? Number(destinationId) : null;

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const eltQuery = useQuery({
    queryKey:
      numericId != null
        ? queryKeys.destinations.eltDetail(numericId, workspaceCode)
        : ["destinations", "elt", "skip"],
    queryFn: async () => {
      const { item } = await fetchEltDestination(numericId!, workspaceCode);
      return item;
    },
    enabled: numericId != null,
  });

  const catalogQuery = useQuery({
    queryKey: queryKeys.destinations.detail(destinationId),
    queryFn: () => loadDestinationCatalogById(destinationId, workspaceCode),
    enabled: Boolean(destinationId),
  });

  const checkMut = useMutation({
    mutationFn: () => postEltDestinationCheck(numericId!, workspaceCode),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
      if (numericId != null) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.destinations.eltDetail(numericId, workspaceCode),
        });
      }
    },
  });

  if (!destinationId) {
    return (
      <div className="p-4" data-testid="state-not-found-destination">
        <p>Приёмник не найден.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2" data-testid="button-back-destinations">
          К списку приёмников
        </LinkAsButton>
      </div>
    );
  }

  const isPending =
    wsQuery.isPending || catalogQuery.isPending || (numericId != null && eltQuery.isPending);
  const isError = catalogQuery.isError || (numericId != null && eltQuery.isError);

  if (isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError) {
    return (
      <div className="p-4" data-testid="state-not-found-destination">
        <p>Приёмник не найден или ошибка API.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2" data-testid="button-back-destinations">
          К списку приёмников
        </LinkAsButton>
      </div>
    );
  }

  const elt = eltQuery.data;
  const catalog = catalogQuery.data;
  const destName = elt?.name ?? catalog?.name ?? destinationId;
  const connectorCode = elt?.connector_code ?? catalog?.connectorCode;
  const connectionCount = catalog?.connectionCount ?? 0;
  const canManage = numericId != null;

  let checkMsg: string | null = null;
  if (checkMut.isSuccess) {
    checkMsg = `${checkMut.data.ok ? "Ок" : "Ошибка"}: ${checkMut.data.message}`;
  } else if (checkMut.isError) {
    checkMsg = formatApiErrorMessage(checkMut.error, "Ошибка проверки");
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={destName}
        description={
          elt
            ? `${elt.connector_code} · id ${elt.id}`
            : `${catalog?.type ?? ""}${catalog?.connectorCode ? ` · ${catalog.connectorCode}` : ""} · ${catalog?.schemaOrDb ?? ""}`
        }
        breadcrumbs={`Интеграции / Приёмники / ${destName}`}
        actions={
          canManage ? (
            <div className="flex flex-wrap gap-2">
              <LinkAsButton
                href={`/destinations/${numericId}/edit`}
                variant="outline"
                data-testid="button-edit-destination"
              >
                Изменить
              </LinkAsButton>
              <ConfirmDeleteButton
                entityLabel={destName}
                testId="button-delete-destination-detail"
                disabled={connectionCount > 0}
                disabledTitle={
                  connectionCount > 0 ? "Сначала удалите подключения, использующие этот приёмник" : undefined
                }
                onDelete={() => deleteEltDestination(numericId!, workspaceCode)}
                onSuccess={() => {
                  void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
                  setLocation("/destinations");
                }}
              />
              <Button
                type="button"
                data-testid="button-check-destination-detail"
                disabled={checkMut.isPending}
                onClick={() => checkMut.mutate()}
              >
                {checkMut.isPending ? "Проверка…" : "Проверить подключение"}
              </Button>
            </div>
          ) : undefined
        }
      />
      <div className="flex gap-2">
        <LinkAsButton href="/destinations" variant="outline" data-testid="button-back-destinations">
          Назад
        </LinkAsButton>
        {canManage ? (
          <LinkAsButton href={`/destinations/${numericId}/edit`} data-testid="button-edit-destination-inline">
            Изменить параметры
          </LinkAsButton>
        ) : null}
      </div>
      {checkMsg ? <p className="text-sm text-muted-foreground">{checkMsg}</p> : null}
      <Card className="p-4" data-testid="destination-detail-overview">
        {connectorCode ? (
          <p className="text-sm" data-testid="destination-detail-connector">
            Коннектор: <span className="font-medium">{connectorCode}</span>
          </p>
        ) : null}
        {elt ? (
          <>
            <p className="text-sm text-muted-foreground">Статус: {elt.status}</p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground" data-testid="destination-config-summary">
              {describeDestinationConfig(
                parseDestinationConfig(
                  isDestinationConnectorCode(elt.connector_code) ? elt.connector_code : "postgres",
                  elt.config ?? {},
                ),
              ).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </>
        ) : null}
      </Card>
      {numericId != null ? (
        <ResourceAccessPanel resourceType="destinations" resourceId={numericId} canManage={canManageAccess} />
      ) : null}
    </div>
  );
}
