import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { fetchV1ConnectorsCatalog } from "@/lib/api-datanorma";
import type { ConnectorCatalogItem } from "@/lib/types";

function mapRole(v: string): ConnectorCatalogItem["role"] {
  if (v === "source" || v === "destination" || v === "both") return v;
  return "source";
}

export function ConnectorsPage() {
  const [q, setQ] = useState("");
  const [role, setRole] = useState<"all" | ConnectorCatalogItem["role"]>("all");
  const [region, setRegion] = useState<"all" | ConnectorCatalogItem["region"]>("all");

  const query = useQuery({
    queryKey: ["connectors-catalog"],
    queryFn: async () => {
      const body = await fetchV1ConnectorsCatalog("all");
      const items = Array.isArray(body.items) ? body.items : [];
      return items.map((x) => ({
        id: String(x.code ?? ""),
        name: String(x.name ?? ""),
        category: String(x.category ?? "Общее"),
        region: "ru" as const,
        role: mapRole(String(x.category ?? "source")),
        preview: false,
        description: String(x.name ?? ""),
        streams: Array.isArray(x.streams) ? x.streams.map((s) => String((s as Record<string, unknown>).stream_name ?? "")) : [],
        auth: "—",
      }));
    },
  });

  const filtered = useMemo(() => {
    if (!query.data) return [];
    return query.data.filter((c) => {
      if (q && !(`${c.name} ${c.category} ${c.description}`.toLowerCase().includes(q.toLowerCase()))) return false;
      if (role === "source" && !(c.role === "source" || c.role === "both")) return false;
      if (role === "destination" && !(c.role === "destination" || c.role === "both")) return false;
      if (role === "both" && c.role !== "both") return false;
      if (region !== "all" && c.region !== region) return false;
      return true;
    });
  }, [query.data, q, role, region]);

  if (query.isLoading) return <div data-testid="state-loading-connectors" className="p-4">Загрузка каталога…</div>;
  if (query.isError || !query.data) return <div data-testid="state-error-connectors" className="p-4">Не удалось загрузить каталог.</div>;

  return (
    <div className="p-4">
      <PageHeader title="Каталог коннекторов" description="Доступные источники и приёмники для интеграций" breadcrumbs="Интеграции / Каталог коннекторов" />
      <div className="mb-4 flex flex-wrap items-end gap-2">
        <Input className="max-w-md" placeholder="Поиск по названию или категории…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="input-connectors-search" />
        <div className="flex flex-wrap gap-2">
          <select className="h-9 rounded-md border bg-background px-2 text-sm" value={role} onChange={(e) => setRole(e.target.value as typeof role)} data-testid="filter-connector-role" aria-label="Тип коннектора">
            <option value="all">Все типы</option>
            <option value="source">Источник</option>
            <option value="destination">Приёмник</option>
            <option value="both">Источник и приёмник</option>
          </select>
          <select className="h-9 rounded-md border bg-background px-2 text-sm" value={region} onChange={(e) => setRegion(e.target.value as typeof region)} data-testid="filter-connector-region" aria-label="Регион">
            <option value="all">Все регионы</option>
            <option value="ru">Российские</option>
            <option value="intl">Международные</option>
          </select>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="grid-connectors">
        {filtered.map((c) => (
          <Card key={c.id} className="flex flex-col p-4" data-testid={`card-connector-${c.id}`}>
            <div className="mb-2 flex flex-wrap gap-1">
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{c.category}</span>
              {c.preview ? <span className="rounded-full bg-info/20 px-2 py-0.5 text-xs text-info">Preview</span> : null}
              <span className="rounded-full bg-secondary px-2 py-0.5 text-xs">{c.role === "both" ? "Источник и приёмник" : c.role === "source" ? "Источник" : "Приёмник"}</span>
              <span className="rounded-full border px-2 py-0.5 text-xs">{c.region === "ru" ? "РФ" : "INTL"}</span>
            </div>
            <p className="text-lg font-semibold">{c.name}</p>
            <p className="mt-1 flex-1 text-sm text-muted-foreground">{c.description}</p>
            <p className="mt-2 text-xs text-muted-foreground">Потоки: {c.streams.join(", ")}</p>
            <p className="text-xs text-muted-foreground">Авторизация: {c.auth}</p>
            <LinkAsButton href={`/connectors/${c.id}`} variant="outline" className="mt-3 w-full" data-testid={`button-open-connector-${c.id}`}>
              Настроить
            </LinkAsButton>
          </Card>
        ))}
      </div>
      {filtered.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="state-empty-connectors-filter">Ничего не найдено по фильтрам.</p> : null}
    </div>
  );
}
