import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { activityEvents } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";

export function ActivityPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["activity"],
    queryFn: async () => {
      await new Promise((r) => setTimeout(r, 200));
      return activityEvents;
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
