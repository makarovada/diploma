import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/app/auth-context";
import { PageFooter } from "@/components/page-footer";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetchV1AuditLog, type AuditLogRowDto } from "@/lib/api-datanorma";
import { ApiError } from "@/lib/api-client";

function resultLabel(r: string): string {
  if (r === "success") return "Успех";
  if (r === "failure") return "Ошибка";
  return r;
}

export function AuditPage() {
  const { user } = useAuth();
  const isPlatformAdmin = Boolean(user?.roles?.includes("platform_admin"));

  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [result, setResult] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [applied, setApplied] = useState({
    actor: "",
    action: "",
    resource_type: "",
    result: "",
    date_from: "",
    date_to: "",
  });
  const [selected, setSelected] = useState<AuditLogRowDto | null>(null);

  const queryKey = useMemo(
    () => ["audit-log", applied] as const,
    [applied],
  );

  const query = useQuery({
    queryKey,
    queryFn: () =>
      fetchV1AuditLog({
        limit: 100,
        actor: applied.actor || undefined,
        action: applied.action || undefined,
        resource_type: applied.resource_type || undefined,
        result: applied.result || undefined,
        date_from: applied.date_from || undefined,
        date_to: applied.date_to || undefined,
      }),
    enabled: isPlatformAdmin,
  });

  if (!isPlatformAdmin) {
    return (
      <div className="p-4" data-testid="audit-forbidden">
        <PageHeader
          title="Аудит"
          description="Журнал доступен только администратору платформы"
          breadcrumbs="Администрирование / Аудит"
        />
        <p className="mt-4 text-sm text-muted-foreground">
          У вашей учётной записи нет права «Журнал аудита». Обратитесь к администратору.
        </p>
        <PageFooter />
      </div>
    );
  }

  if (query.isPending) {
    return <div data-testid="state-loading-audit" className="p-4">Загрузка журнала аудита…</div>;
  }

  if (query.isError) {
    const msg =
      query.error instanceof ApiError && query.error.status === 403
        ? "Недостаточно прав для просмотра аудита."
        : "Не удалось загрузить аудит.";
    return (
      <div data-testid="state-error-audit" className="p-4">
        {msg}
      </div>
    );
  }

  const items = query.data?.items ?? [];

  return (
    <div className="p-4">
      <PageHeader title="Аудит" description="Действия пользователей и изменения в workspace" breadcrumbs="Администрирование / Аудит" />
      <div className="mb-4 flex flex-wrap items-end gap-2">
        <div className="flex min-w-[140px] flex-col gap-1">
          <label className="text-xs text-muted-foreground" htmlFor="audit-actor">
            Актор (логин)
          </label>
          <Input id="audit-actor" value={actor} onChange={(e) => setActor(e.target.value)} placeholder="username" data-testid="input-audit-actor" />
        </div>
        <div className="flex min-w-[140px] flex-col gap-1">
          <label className="text-xs text-muted-foreground" htmlFor="audit-action">
            Действие
          </label>
          <Input id="audit-action" value={action} onChange={(e) => setAction(e.target.value)} placeholder="login_success" data-testid="input-audit-action" />
        </div>
        <div className="flex min-w-[120px] flex-col gap-1">
          <label className="text-xs text-muted-foreground" htmlFor="audit-rtype">
            Тип ресурса
          </label>
          <Input
            id="audit-rtype"
            value={resourceType}
            onChange={(e) => setResourceType(e.target.value)}
            placeholder="connection"
            data-testid="input-audit-resource-type"
          />
        </div>
        <div className="flex w-28 flex-col gap-1">
          <label className="text-xs text-muted-foreground" htmlFor="audit-result">
            Результат
          </label>
          <Input id="audit-result" value={result} onChange={(e) => setResult(e.target.value)} placeholder="success" data-testid="input-audit-result" />
        </div>
        <div className="flex min-w-[130px] flex-col gap-1">
          <label className="text-xs text-muted-foreground" htmlFor="audit-df">
            Дата с
          </label>
          <Input id="audit-df" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} data-testid="input-audit-date-from" />
        </div>
        <div className="flex min-w-[130px] flex-col gap-1">
          <label className="text-xs text-muted-foreground" htmlFor="audit-dt">
            Дата по
          </label>
          <Input id="audit-dt" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} data-testid="input-audit-date-to" />
        </div>
        <Button
          type="button"
          variant="default"
          data-testid="button-audit-apply"
          onClick={() =>
            setApplied({
              actor,
              action,
              resource_type: resourceType,
              result,
              date_from: dateFrom,
              date_to: dateTo,
            })
          }
        >
          Применить
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_minmax(280px,360px)]">
        <div className="overflow-auto rounded-lg border" data-testid="table-audit">
          <table className="w-full min-w-[900px] text-left text-sm" aria-label="Журнал аудита">
            <thead className="bg-muted">
              <tr>
                <th className="px-2 py-2">Время</th>
                <th className="px-2 py-2">Кто</th>
                <th className="px-2 py-2">Действие</th>
                <th className="px-2 py-2">Ресурс</th>
                <th className="px-2 py-2">Результат</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr
                  key={a.id}
                  className={`cursor-pointer border-t hover:bg-muted/50 ${selected?.id === a.id ? "bg-muted/60" : ""}`}
                  data-testid={`row-audit-${a.id}`}
                  onClick={() => setSelected(a)}
                >
                  <td className="whitespace-nowrap px-2 py-2 text-xs">{a.created_at ?? "—"}</td>
                  <td className="px-2 py-2">{a.actor_username ?? "—"}</td>
                  <td className="px-2 py-2 font-mono text-xs">{a.action}</td>
                  <td className="px-2 py-2 text-xs">
                    {a.resource_type ?? "—"} {a.resource_id != null ? `#${a.resource_id}` : ""}
                  </td>
                  <td className="px-2 py-2">{resultLabel(a.result)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 ? <p className="p-4 text-sm text-muted-foreground">Записей не найдено.</p> : null}
        </div>

        <Card className="h-fit p-4" data-testid="panel-audit-details">
          <p className="text-sm font-semibold">Детали записи</p>
          {selected ? (
            <dl className="mt-3 space-y-2 text-xs">
              <div>
                <dt className="text-muted-foreground">id</dt>
                <dd className="font-mono">{selected.id}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">workspace_id</dt>
                <dd>{selected.workspace_id ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">IP</dt>
                <dd className="break-all">{selected.ip_address ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">User-Agent</dt>
                <dd className="max-h-24 overflow-auto break-all text-muted-foreground">{selected.user_agent ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">payload_json</dt>
                <dd>
                  <pre className="mt-1 max-h-48 overflow-auto rounded border bg-muted/30 p-2 text-[11px] leading-snug">
                    {selected.payload_json != null ? JSON.stringify(selected.payload_json, null, 2) : "—"}
                  </pre>
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">Выберите строку в таблице.</p>
          )}
        </Card>
      </div>
      <PageFooter />
    </div>
  );
}
