import { useQuery } from "@tanstack/react-query";
import {
  connections,
  connectorHealth,
  dashboardForceEmptyState,
  dashboardKpis,
  dashboardRunsByDay,
  issues,
  runs,
} from "@/lib/mock-data";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      await new Promise((r) => setTimeout(r, 250));
      return { dashboardKpis, runs, issues, hasConnections: connections.length > 0 && !dashboardForceEmptyState };
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

  const scale = 4;

  return (
    <div className="p-4">
      <PageHeader title="Дашборд" description="Текущее состояние интеграций и качества данных" breadcrumbs="Обзор / Дашборд" actions={<LinkAsButton href="/connections/new" data-testid="button-create-connection">Создать подключение</LinkAsButton>} />
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
          <p className="mb-3 text-xs text-muted-foreground">Столбцы: успех / частично / ошибка / выполняется</p>
          <div className="flex h-44 items-end gap-2">
            {dashboardRunsByDay.map((d) => (
              <div key={d.day} className="flex flex-1 flex-col items-center gap-1" data-testid={`chart-bar-${d.day}`}>
                <div className="flex w-full max-w-[2.5rem] flex-col justify-end gap-px overflow-hidden rounded-t bg-muted">
                  {d.running > 0 ? <div className="w-full bg-info" style={{ height: d.running * scale }} title={`running ${d.running}`} /> : null}
                  {d.failed > 0 ? <div className="w-full bg-destructive" style={{ height: d.failed * scale }} title={`failed ${d.failed}`} /> : null}
                  {d.partial > 0 ? <div className="w-full bg-warning" style={{ height: d.partial * scale }} title={`partial ${d.partial}`} /> : null}
                  {d.success > 0 ? <div className="w-full bg-success" style={{ height: d.success * scale }} title={`success ${d.success}`} /> : null}
                </div>
                <span className="text-[10px] text-muted-foreground">{d.day}</span>
              </div>
            ))}
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
            <LinkAsButton href="/runs/run-899" variant="outline" className="justify-start" data-testid="quick-retry-failed">
              Повторить последний сбой
            </LinkAsButton>
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Card className="p-4" data-testid="list-latest-runs">
          <h2 className="mb-2 text-lg font-semibold">Последние запуски</h2>
          {data.runs.map((run) => (
            <div className="mb-2 flex items-center justify-between text-sm" key={run.id}>
              <span>{run.connectionName}</span>
              <StatusBadge status={run.status} />
            </div>
          ))}
        </Card>
        <Card className="p-4" data-testid="list-open-issues">
          <h2 className="mb-2 text-lg font-semibold">Проблемы, требующие внимания</h2>
          {data.issues.map((item) => (
            <div key={item.id} className="mb-2 text-sm">
              {item.type} · {item.field}
            </div>
          ))}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card className="p-4" data-testid="dashboard-connector-health">
          <h2 className="mb-2 text-lg font-semibold">Health коннекторов</h2>
          <ul className="space-y-2 text-sm">
            {connectorHealth.map((h) => (
              <li key={h.id} className="flex items-start justify-between gap-2" data-testid={`dashboard-health-${h.id}`}>
                <span>{h.name}</span>
                <span
                  className={cn(
                    "text-xs",
                    h.status === "ok" && "text-success",
                    h.status === "warning" && "text-warning",
                  )}
                >
                  {h.detail}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-4" data-testid="dashboard-onboarding-checklist">
          <h2 className="mb-2 text-lg font-semibold">Чеклист онбординга</h2>
          <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
            <li>Создайте источник и приёмник</li>
            <li>Настройте маппинг и нормализацию</li>
            <li>Запустите первую синхронизацию</li>
          </ol>
          <LinkAsButton href="/onboarding" variant="outline" className="mt-3" data-testid="button-open-full-onboarding">
            Полный чеклист
          </LinkAsButton>
        </Card>
      </div>
    </div>
  );
}
