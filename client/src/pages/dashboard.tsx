import { useQuery } from "@tanstack/react-query";
import type { NormIssueRowDto, V1SyncRunItem } from "@/lib/api-types";
import {
  fetchNormalizationIssues,
  fetchSalesSummary,
  fetchStagingCounts,
  fetchV1Connections,
  fetchV1Syncs,
  mapNormRowToIssue,
  mapV1SyncToRun,
  mapV1ToConnection,
} from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

const soft = { suppressGlobalAuthHandlers: true } as const;

function runsByLast7Days(items: V1SyncRunItem[]) {
  const days: { day: string; success: number; partial: number; failed: number; running: number }[] = [];
  const now = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const label = d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
    days.push({ day: label, success: 0, partial: 0, failed: 0, running: 0 });
  }
  const labelForIso = (iso: string) => {
    const x = new Date(iso);
    return x.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
  };
  const labels = new Set(days.map((d) => d.day));
  for (const s of items) {
    if (!s.started_at) continue;
    const k = labelForIso(s.started_at);
    if (!labels.has(k)) continue;
    const bucket = days.find((d) => d.day === k)!;
    const st = s.status.toLowerCase();
    if (st === "success") bucket.success += 1;
    else if (st === "failed") bucket.failed += 1;
    else if (st === "partial") bucket.partial += 1;
    else if (st === "running" || st === "queued") bucket.running += 1;
  }
  return days;
}

function msInLast24h(iso: string | null): boolean {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return Date.now() - t <= 24 * 60 * 60 * 1000;
}

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.dashboard.root(),
    queryFn: async () => {
      const [connsRes, syncsRes, salesRes, normRes, stagingRes] = await Promise.all([
        fetchV1Connections(),
        fetchV1Syncs(500),
        fetchSalesSummary(soft).catch(() => null),
        fetchNormalizationIssues(200, soft).catch(() => ({ rows: [] as NormIssueRowDto[] })),
        fetchStagingCounts(soft).catch(() => null),
      ]);
      const connections = connsRes.items.map(mapV1ToConnection);
      const syncItems = syncsRes.items;
      const runs = syncItems.slice(0, 8).map(mapV1SyncToRun);
      const issues = (normRes.rows ?? []).slice(0, 8).map(mapNormRowToIssue);
      const hasConnections = connections.length > 0;
      const chart = runsByLast7Days(syncItems);

      const success24 = syncItems.filter((s) => s.status.toLowerCase() === "success" && msInLast24h(s.started_at)).length;
      const failed24 = syncItems.filter((s) => s.status.toLowerCase() === "failed" && msInLast24h(s.started_at)).length;
      const finished = syncItems.filter((s) => s.finished_at && s.started_at && s.status.toLowerCase() === "success");
      const avgSec =
        finished.length > 0
          ? Math.round(
              finished.reduce((acc, s) => {
                const a = new Date(s.started_at!).getTime();
                const b = new Date(s.finished_at!).getTime();
                return acc + (b - a) / 1000;
              }, 0) / finished.length,
            )
          : 0;
      const avgMin = Math.floor(avgSec / 60);
      const avgS = avgSec % 60;
      const avgLabel = finished.length > 0 ? `${String(avgMin).padStart(2, "0")}:${String(avgS).padStart(2, "0")}` : "—";

      let normPct = "—";
      if (stagingRes && normRes.rows) {
        const total = stagingRes.raw_google_sheet_orders_staging;
        if (total > 0) {
          const iss = normRes.rows.length;
          normPct = `${Math.max(0, Math.min(100, ((total - iss) / total) * 100)).toFixed(1)}%`;
        }
      }

      const integrations = [...new Set(connsRes.items.map((i) => i.integration_code))].slice(0, 6);
      const health: { id: string; name: string; status: "ok" | "warning"; detail: string }[] = integrations.map((code) => ({
        id: code,
        name: code,
        status: "ok",
        detail: "Запись в sync_state",
      }));

      const lastFailed = syncItems.find((s) => s.status.toLowerCase() === "failed");

      const dashboardKpis = [
        { label: "Активные подключения", value: String(connections.length) },
        { label: "Успешные запуски за 24ч", value: String(success24) },
        { label: "Запуски с ошибками (24ч)", value: String(failed24) },
        { label: "Проблемные записи (витрина)", value: String(normRes.rows?.length ?? 0) },
        { label: "Среднее время sync (успех)", value: avgLabel },
        { label: "Нормализовано (оценка)", value: normPct },
      ];

      const salesRow = salesRes?.row_count;

      return {
        dashboardKpis,
        runs,
        issues,
        hasConnections,
        chart,
        connectorHealth: health,
        salesRow,
        quickFailedHref: lastFailed ? `/runs/${lastFailed.id}` : "/runs",
      };
    },
  });

  if (isLoading) return <div data-testid="state-loading-dashboard" className="p-4">Загрузка дашборда...</div>;
  if (isError || !data) return <div data-testid="state-error-dashboard" className="p-4">Не удалось загрузить дашборд.</div>;

  if (!data.hasConnections) {
    return (
      <div className="p-4">
        <PageHeader title="Дашборд" description="Обзор интеграций" breadcrumbs="Обзор / Дашборд" />
        <Card className="mx-auto max-w-lg p-8 text-center" data-testid="dashboard-empty-state">
          <h2 className="text-lg font-semibold">Начните с первого подключения</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Выберите источник, приёмник и настройте правила нормализации. DataNorma проведёт вас по шагам.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <LinkAsButton href="/connections/new" data-testid="button-empty-create-connection">
              Создать подключение
            </LinkAsButton>
            <LinkAsButton href="/connectors" variant="outline" data-testid="button-empty-catalog">
              Открыть каталог коннекторов
            </LinkAsButton>
          </div>
        </Card>
      </div>
    );
  }

  const maxBar = Math.max(1, ...data.chart.map((d) => d.success + d.partial + d.failed + d.running));

  return (
    <div className="p-4">
      <PageHeader title="Дашборд" description="Текущее состояние интеграций и качества данных" breadcrumbs="Обзор / Дашборд" actions={<LinkAsButton href="/connections/new" data-testid="button-create-connection">Создать подключение</LinkAsButton>} />
      {data.salesRow != null ? (
        <p className="mb-2 text-xs text-muted-foreground" data-testid="dashboard-sales-summary">
          Витрина sales: {data.salesRow.toLocaleString("ru-RU")} строк
        </p>
      ) : null}
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6" data-testid="kpi-grid">
        {data.dashboardKpis.map((kpi) => (
          <Card key={kpi.label} className="p-3">
            <p className="text-xs text-muted-foreground">{kpi.label}</p>
            <p className="text-lg font-semibold">{kpi.value}</p>
          </Card>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="p-4 lg:col-span-2" data-testid="dashboard-chart-runs">
          <h2 className="mb-3 text-lg font-semibold">Запуски за 7 дней</h2>
          <p className="mb-3 text-xs text-muted-foreground">По данным /api/v1/syncs (успех / частично / ошибка / в очереди)</p>
          <div className="flex h-44 items-end gap-2">
            {data.chart.map((d) => {
              const h = (v: number) => Math.max(2, Math.round((v / maxBar) * 80));
              return (
                <div key={d.day} className="flex flex-1 flex-col items-center gap-1" data-testid={`chart-bar-${d.day}`}>
                  <div className="flex w-full max-w-[2.5rem] flex-col justify-end gap-px overflow-hidden rounded-t bg-muted">
                    {d.running > 0 ? <div className="w-full bg-info" style={{ height: h(d.running) }} title={`running ${d.running}`} /> : null}
                    {d.failed > 0 ? <div className="w-full bg-destructive" style={{ height: h(d.failed) }} title={`failed ${d.failed}`} /> : null}
                    {d.partial > 0 ? <div className="w-full bg-warning" style={{ height: h(d.partial) }} title={`partial ${d.partial}`} /> : null}
                    {d.success > 0 ? <div className="w-full bg-success" style={{ height: h(d.success) }} title={`success ${d.success}`} /> : null}
                  </div>
                  <span className="text-[10px] text-muted-foreground">{d.day}</span>
                </div>
              );
            })}
          </div>
        </Card>
        <Card className="p-4" data-testid="dashboard-quick-actions">
          <h2 className="mb-2 text-lg font-semibold">Быстрые действия</h2>
          <div className="flex flex-col gap-2">
            <LinkAsButton href="/connections/new" className="justify-start" data-testid="quick-create-connection">
              Создать подключение
            </LinkAsButton>
            <LinkAsButton href="/sources/new" variant="outline" className="justify-start" data-testid="quick-add-source">
              Добавить источник
            </LinkAsButton>
            <LinkAsButton href="/destinations/new" variant="outline" className="justify-start" data-testid="quick-add-destination">
              Добавить приёмник
            </LinkAsButton>
            <LinkAsButton href="/issues" variant="outline" className="justify-start" data-testid="quick-open-issues">
              Проблемные записи
            </LinkAsButton>
            <LinkAsButton href={data.quickFailedHref} variant="outline" className="justify-start" data-testid="quick-retry-failed">
              Последний сбой / запуски
            </LinkAsButton>
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Card className="p-4" data-testid="list-latest-runs">
          <h2 className="mb-2 text-lg font-semibold">Последние запуски</h2>
          {data.runs.length === 0 ? <p className="text-sm text-muted-foreground">Нет данных.</p> : null}
          {data.runs.map((run) => (
            <div className="mb-2 flex items-center justify-between text-sm" key={run.id}>
              <span>{run.connectionName}</span>
              <StatusBadge status={run.status} />
            </div>
          ))}
        </Card>
        <Card className="p-4" data-testid="list-open-issues">
          <h2 className="mb-2 text-lg font-semibold">Проблемы, требующие внимания</h2>
          {data.issues.length === 0 ? <p className="text-sm text-muted-foreground">Нет записей в normalization_issue.</p> : null}
          {data.issues.map((item) => (
            <div key={item.id} className="mb-2 text-sm">
              {item.type} · {item.field}
            </div>
          ))}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card className="p-4" data-testid="dashboard-connector-health">
          <h2 className="mb-2 text-lg font-semibold">Интеграции</h2>
          <ul className="space-y-2 text-sm">
            {data.connectorHealth.map((h) => (
              <li key={h.id} className="flex items-start justify-between gap-2" data-testid={`dashboard-health-${h.id}`}>
                <span>{h.name}</span>
                <span className={cn("text-xs", h.status === "ok" && "text-success", h.status === "warning" && "text-warning")}>{h.detail}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-4" data-testid="dashboard-onboarding-checklist">
          <h2 className="mb-2 text-lg font-semibold">Первые шаги</h2>
          <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
            <li>Создайте источник и приёмник</li>
            <li>Настройте подключение в мастере</li>
            <li>Запустите первую синхронизацию</li>
          </ol>
          <LinkAsButton href="/connections/new" variant="outline" className="mt-3" data-testid="button-open-full-onboarding">
            Создать подключение
          </LinkAsButton>
        </Card>
      </div>
    </div>
  );
}
