import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { fetchDbtModels, fetchDbtModelPreview } from "@/lib/api-datanorma";
import { ApiError } from "@/lib/api-client";
import type { DbtModelItemDto } from "@/lib/api-types";

const DOMAIN_ORDER = ["marketing", "ecommerce", "crm", "operations", "other"];

const DOMAIN_LABELS: Record<string, string> = {
  marketing: "Marketing",
  ecommerce: "Ecommerce",
  crm: "CRM",
  operations: "Operations",
  other: "Прочее",
};

function groupByDomain(items: DbtModelItemDto[]) {
  const map = new Map<string, DbtModelItemDto[]>();
  for (const m of items) {
    const d = (m.domain || "other").toLowerCase();
    if (!map.has(d)) map.set(d, []);
    map.get(d)!.push(m);
  }
  for (const [, list] of map) {
    list.sort((a, b) => a.name.localeCompare(b.name));
  }
  const keys = Array.from(map.keys()).sort((a, b) => {
    const ia = DOMAIN_ORDER.indexOf(a);
    const ib = DOMAIN_ORDER.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });
  return keys.map((domain) => ({ domain, models: map.get(domain)! }));
}

export function SemanticLayerPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dbt-models"],
    queryFn: async () => {
      const r = await fetchDbtModels();
      return { items: r.items, source: r.source ?? "unknown", fromApi: true as const };
    },
  });

  const items = data?.items ?? [];
  const grouped = useMemo(() => groupByDomain(items), [items]);

  const [selectedName, setSelectedName] = useState<string | null>(null);
  const selected = useMemo(() => {
    if (items.length === 0) return undefined;
    if (selectedName) {
      return items.find((m) => m.name === selectedName) ?? items[0];
    }
    return items[0];
  }, [items, selectedName]);

  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const loadPreview = useCallback(async () => {
    if (!selected) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const r = await fetchDbtModelPreview(selected.name, {
        limit: 25,
        schema: selected.schema || "semantic",
      });
      setPreviewRows(r.rows);
    } catch (e) {
      setPreviewRows(null);
      if (e instanceof ApiError) {
        setPreviewError(e.body || e.message);
      } else {
        setPreviewError(e instanceof Error ? e.message : "Ошибка запроса");
      }
    } finally {
      setPreviewLoading(false);
    }
  }, [selected]);

  const previewColumns = useMemo(() => {
    if (!previewRows?.length) return [];
    return Object.keys(previewRows[0] ?? {});
  }, [previewRows]);

  return (
    <div className="p-4">
      <PageHeader
        title="Семантический слой"
        description="Бизнес-витрины из dbt поверх normalized; preview читает materialized таблицы в PostgreSQL (schema semantic по умолчанию)."
        breadcrumbs="Данные / Семантический слой"
      />

      {!isLoading && data?.fromApi === true && (
        <p className="mb-2 text-xs text-muted-foreground">
          Источник каталога: <span className="font-mono">{data.source}</span>
          {data.source === "sql" ? " (dbt/models/**/*.sql)" : ""}
          {data.source === "manifest" ? " (dbt/target/manifest.json)" : ""}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <Card className="max-h-[70vh] overflow-y-auto p-2" data-testid="semantic-model-list">
          <p className="px-2 py-1 text-xs font-medium text-muted-foreground">Модели по домену</p>
          {isLoading ? (
            <p className="px-2 text-sm text-muted-foreground">Загрузка…</p>
          ) : grouped.length === 0 ? (
            <p className="px-2 text-sm text-muted-foreground">Нет моделей в dbt/models.</p>
          ) : (
            grouped.map(({ domain, models }) => (
              <div key={domain} className="mb-3">
                <p className="px-2 py-1 text-xs font-semibold uppercase text-muted-foreground">
                  {DOMAIN_LABELS[domain] ?? domain}
                </p>
                <ul className="space-y-1">
                  {models.map((m) => (
                    <li key={m.name}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedName(m.name);
                          setPreviewRows(null);
                          setPreviewError(null);
                        }}
                        className={cn(
                          "w-full rounded-md px-2 py-2 text-left text-sm",
                          selected?.name === m.name ? "bg-secondary font-medium" : "hover:bg-muted",
                        )}
                        data-testid={`semantic-model-${m.name}`}
                      >
                        <div className="font-mono text-xs">{m.name}</div>
                        <div className="text-xs text-muted-foreground">{m.schema}</div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </Card>

        <Card className="overflow-auto p-0" data-testid="semantic-model-detail">
          {selected ? (
            <div className="p-4">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="font-mono text-base font-semibold">{selected.name}</h3>
                  <p className="text-sm text-muted-foreground">{selected.description || "—"}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    schema: {selected.schema} · materialized: {selected.materialized_as}
                    {selected.path ? ` · ${selected.path}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    источники (normalized/raw): {selected.sources.length ? selected.sources.join(", ") : "—"}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="default"
                  disabled={previewLoading}
                  onClick={() => void loadPreview()}
                  data-testid="semantic-preview-button"
                >
                  {previewLoading ? "Загрузка…" : "Preview (semantic.*)"}
                </Button>
              </div>

              <h4 className="mb-2 text-sm font-medium">Колонки</h4>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm" aria-label={`Колонки ${selected.name}`}>
                  <thead className="bg-muted">
                    <tr>
                      <th>Имя</th>
                      <th>Тип</th>
                      <th>PK</th>
                      <th>Описание</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.columns?.length ? selected.columns : []).map((c) => (
                      <tr key={c.name} className="border-t">
                        <td className="font-mono text-xs">{c.name}</td>
                        <td>{c.dataType}</td>
                        <td>{c.isPrimaryKey ? "да" : "—"}</td>
                        <td className="text-muted-foreground">{c.description || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!selected.columns?.length ? (
                  <p className="p-2 text-xs text-muted-foreground">
                    Колонки не разобраны (запустите <span className="font-mono">dbt compile</span> для manifest или проверьте SELECT … AS в SQL).
                  </p>
                ) : null}
              </div>

              {previewError ? (
                <div
                  className="mt-4 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm"
                  data-testid="semantic-preview-error"
                >
                  <strong>Preview недоступен.</strong> Таблица могла ещё не быть создана — выполните{" "}
                  <span className="font-mono">dbt run</span>. Детали: {previewError}
                </div>
              ) : null}

              {previewRows && previewRows.length > 0 ? (
                <div className="mt-4" data-testid="semantic-preview-table-wrap">
                  <h4 className="mb-2 text-sm font-medium">Строки (sample)</h4>
                  <div className="overflow-x-auto rounded-md border">
                    <table className="w-full min-w-[480px] text-left text-xs">
                      <thead className="bg-muted">
                        <tr>
                          {previewColumns.map((col) => (
                            <th key={col} className="whitespace-nowrap px-2 py-1 font-mono">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.map((row, i) => (
                          <tr key={i} className="border-t">
                            {previewColumns.map((col) => (
                              <td key={col} className="max-w-[240px] truncate px-2 py-1 font-mono">
                                {formatCell(row[col])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">Выберите модель.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
