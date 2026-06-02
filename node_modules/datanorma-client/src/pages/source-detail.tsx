import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useRoute, useLocation } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { queryKeys } from "@/lib/query-keys";
import { fetchWorkspaces, formatTs } from "@/lib/api-datanorma";
import { deleteEltSource, fetchEltSource, postEltSourceCheck } from "@/lib/api-elt";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { ApiError } from "@/lib/api-client";
import {
  hasGoogleOAuthCallback,
  OAUTH_WIZARD_RESTORE_KEY,
} from "@/lib/oauth-return";
import { ResourceAccessPanel } from "@/components/resource-access-panel";
import { useAuth } from "@/app/auth-context";
import { usePermission } from "@/hooks/use-permission";

export function SourceDetailPage() {
  const [, params] = useRoute("/sources/:sourceId");
  const [, setLocation] = useLocation();
  const rawId = params?.sourceId ? decodeURIComponent(params.sourceId) : "";
  const idPart = rawId.split("?")[0]?.split("&")[0] ?? rawId;
  const sourceId = /^\d+$/.test(idPart) ? Number(idPart) : null;
  const isNewAlias = idPart === "new" || rawId.startsWith("new");
  const oauthReturn = hasGoogleOAuthCallback();

  useEffect(() => {
    if (isNewAlias) {
      setLocation("/sources/new");
      return;
    }
    if (sourceId != null || !oauthReturn) return;
    try {
      const raw = sessionStorage.getItem(OAUTH_WIZARD_RESTORE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as { returnPath?: string };
        const target = saved.returnPath?.trim();
        if (target?.startsWith("/connections/new")) {
          const pathOnly = target.split("?")[0];
          setLocation(pathOnly);
          return;
        }
      }
    } catch {
      /* ignore */
    }
    setLocation("/connections/new");
  }, [isNewAlias, sourceId, oauthReturn, setLocation]);

  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManageAccess = Boolean(user?.is_workspace_admin) || usePermission("source.delete");

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

  const checkMut = useMutation({
    mutationFn: () => postEltSourceCheck(sourceId!, workspaceCode),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltList(workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltDetail(sourceId!, workspaceCode) });
    },
  });

  if (isNewAlias || (oauthReturn && sourceId == null)) {
    return (
      <div className="p-4 text-muted-foreground" data-testid="state-source-redirect">
        Возврат после Google OAuth…
      </div>
    );
  }

  if (!sourceId) {
    return (
      <div className="p-4" data-testid="state-not-found-source">
        <p>Укажите числовой id источника в адресе (например /sources/12).</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2" data-testid="button-back-sources">
          К списку источников
        </LinkAsButton>
        <LinkAsButton href="/sources/new" className="ml-2 mt-2" data-testid="button-go-source-new">
          Создать источник
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending || wsQuery.isPending) {
    return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  }
  if (query.isError || !query.data) {
    return (
      <div className="p-4" data-testid="state-not-found-source">
        <p>Источник не найден или ошибка API.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2" data-testid="button-back-sources">
          К списку источников
        </LinkAsButton>
      </div>
    );
  }

  const source = query.data;
  let checkMsg: string | null = null;
  if (checkMut.isSuccess) {
    checkMsg = `${checkMut.data.ok ? "Ок" : "Ошибка"}: ${checkMut.data.message}`;
  } else if (checkMut.isError) {
    checkMsg = checkMut.error instanceof ApiError ? checkMut.error.message : "Ошибка проверки";
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={source.name}
        description={`Коннектор: ${source.connector_code} · id ${source.id}`}
        breadcrumbs={`Интеграции / Источники / ${source.name}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <LinkAsButton href={`/sources/${sourceId}/edit`} variant="outline" data-testid="button-edit-source">
              Изменить
            </LinkAsButton>
            <ConfirmDeleteButton
              entityLabel={source.name}
              testId="button-delete-source-detail"
              onDelete={() => deleteEltSource(sourceId, workspaceCode)}
              onSuccess={() => {
                void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltList(workspaceCode) });
                setLocation("/sources");
              }}
            />
            <Button
              type="button"
              data-testid="button-test-source"
              disabled={checkMut.isPending}
              onClick={() => checkMut.mutate()}
            >
              {checkMut.isPending ? "Проверка…" : "Проверить подключение"}
            </Button>
          </div>
        }
      />
      <div className="flex flex-wrap gap-2">
        <LinkAsButton href="/sources" variant="outline" data-testid="button-back-sources">
          Назад
        </LinkAsButton>
        <LinkAsButton
          href={`/connections/new?source=${encodeURIComponent(String(source.id))}`}
          data-testid="button-create-connection-from-source"
        >
          Создать подключение
        </LinkAsButton>
      </div>
      {checkMsg ? <p className="text-sm text-muted-foreground">{checkMsg}</p> : null}
      <Card className="p-4" data-testid="source-detail-overview">
        <p className="text-sm text-muted-foreground">Статус: {source.status}</p>
        <p className="text-sm text-muted-foreground">Обновлён: {formatTs(source.updated_at)}</p>
        <p className="text-sm text-muted-foreground">Проверка: {formatTs(source.last_checked_at)}</p>
        <p className="mt-2 text-xs text-muted-foreground font-mono break-all">
          config: {JSON.stringify(source.config ?? {})}
        </p>
      </Card>
      <ResourceAccessPanel resourceType="sources" resourceId={sourceId} canManage={canManageAccess} />
    </div>
  );
}
