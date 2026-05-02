import { useQuery } from "@tanstack/react-query";
import { sources } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Input } from "@/components/ui/input";

const checkLabel: Record<string, string> = {
  ok: "Проверено",
  warning: "Предупреждение",
  error: "Ошибка",
  never: "Не проверялось",
};

export function SourcesPage() {
  const query = useQuery({
    queryKey: ["sources"],
    queryFn: async () => {
      await new Promise((r) => setTimeout(r, 150));
      return sources;
    },
  });

  if (query.isLoading) return <div data-testid="state-loading-sources" className="p-4">Загрузка источников…</div>;
  if (query.isError) return <div data-testid="state-error-sources" className="p-4">Ошибка загрузки источников.</div>;
  const list = query.data ?? [];
  if (list.length === 0) {
    return (
      <div className="p-4">
        <PageHeader title="Источники" description="Сохранённые подключения к системам-источникам" breadcrumbs="Интеграции / Источники" actions={<LinkAsButton href="/sources/new" data-testid="button-add-source">Добавить источник</LinkAsButton>} />
        <div data-testid="state-empty-sources" className="rounded-lg border bg-card p-8 text-center">
          <p className="font-medium">Источников пока нет</p>
          <p className="mt-1 text-sm text-muted-foreground">Создайте источник из каталога коннекторов.</p>
          <LinkAsButton href="/sources/new" className="mt-4" data-testid="button-empty-create-source">Создать источник</LinkAsButton>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <PageHeader title="Источники" description="Сохранённые подключения к системам-источникам" breadcrumbs="Интеграции / Источники" actions={<LinkAsButton href="/sources/new" data-testid="button-add-source">Добавить источник</LinkAsButton>} />
      <div className="mb-3 flex flex-wrap gap-2">
        <Input className="max-w-sm" placeholder="Поиск по названию или коннектору…" data-testid="input-sources-search" />
      </div>
      <div className="overflow-auto rounded-lg border" data-testid="table-sources">
        <table className="w-full min-w-[960px] text-left text-sm" aria-label="Таблица источников">
          <thead className="bg-muted">
            <tr>
              <th>Название</th>
              <th>Коннектор</th>
              <th>Категория</th>
              <th>Проверка</th>
              <th>Потоки</th>
              <th>Последнее использование</th>
              <th>Владелец</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.map((s) => (
              <tr key={s.id} className="border-t" data-testid={`row-source-${s.id}`}>
                <td>{s.name}</td>
                <td>{s.connector}</td>
                <td>{s.category}</td>
                <td>{checkLabel[s.checkStatus]}</td>
                <td>{s.streamCount}</td>
                <td>{s.lastUsed}</td>
                <td>{s.owner}</td>
                <td>
                  <LinkAsButton href={`/sources/${s.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-source-${s.id}`}>
                    Открыть
                  </LinkAsButton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
