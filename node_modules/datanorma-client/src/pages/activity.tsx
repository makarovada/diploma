import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { fetchV1Activity, formatTs } from "@/lib/api-datanorma";
import type { ActivityEvent } from "@/lib/types";

function mapActivityEvent(row: Record<string, unknown>, idx: number): ActivityEvent {
  const action = String(row.action ?? "action");
  const actor = String(row.actor ?? "system");
  const details = String(row.details ?? "");
  return {
    id: String(row.id ?? `activity-${idx}`),
    at: formatTs((row.created_at as string | null | undefined) ?? null),
    type: "config",
    title: `${action}`,
    detail: `${actor}${details ? ` · ${details}` : ""}`,
  };
}

export function ActivityPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["activity"],
    queryFn: async () => {
      const resp = await fetchV1Activity();
      return resp.items.map(mapActivityEvent);
    },
  });

  if (isLoading) return <div data-testid="state-loading-activity" className="p-4">Загрузка ленты активности…</div>;
  if (isError || !data) return <div data-testid="state-error-activity" className="p-4">Не удалось загрузить активность.</div>;
  if (data.length === 0) return <div data-testid="state-empty-activity" className="p-4">Событий пока нет.</div>;

  return (
    <div className="p-4">
      <PageHeader title="Активность" description="События по подключениям, запускам и настройкам" breadcrumbs="Обзор / Активность" />
      <Card className="divide-y p-0" data-testid="list-activity">
        {data.map((ev) => (
          <div key={ev.id} className="flex gap-3 p-4" data-testid={`row-activity-${ev.id}`}>
            <Activity className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{ev.title}</p>
              <p className="text-xs text-muted-foreground">{ev.detail}</p>
              <p className="mt-1 text-xs text-muted-foreground">{ev.at}</p>
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
