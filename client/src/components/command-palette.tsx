import { useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { Search } from "lucide-react";
import { connections, connectorsCatalog, issues, runs } from "@/lib/mock-data";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type PaletteItem = { id: string; label: string; hint: string; href: string };

function buildItems(): PaletteItem[] {
  const c = connections.map((x) => ({
    id: `conn-${x.id}`,
    label: x.name,
    hint: "Подключение",
    href: `/connections/${x.id}`,
  }));
  const r = runs.map((x) => ({
    id: `run-${x.id}`,
    label: `${x.id} · ${x.connectionName}`,
    hint: "Запуск",
    href: `/runs/${x.id}`,
  }));
  const i = issues.map((x) => ({
    id: `issue-${x.id}`,
    label: `${x.type} · ${x.field}`,
    hint: "Проблемная запись",
    href: `/issues/${x.id}`,
  }));
  const conn = connectorsCatalog.map((x) => ({
    id: `connector-${x.id}`,
    label: x.name,
    hint: "Коннектор",
    href: `/connectors/${x.id}`,
  }));
  return [
    { id: "nav-settings", label: "Настройки", hint: "Раздел", href: "/settings" },
    { id: "nav-norm", label: "Нормализация", hint: "Раздел", href: "/normalization" },
    ...c,
    ...r,
    ...i,
    ...conn,
  ];
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [, setLocation] = useLocation();
  const [q, setQ] = useState("");
  const items = useMemo(() => buildItems(), []);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return items.slice(0, 12);
    return items.filter((it) => it.label.toLowerCase().includes(s) || it.hint.toLowerCase().includes(s)).slice(0, 20);
  }, [items, q]);

  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh]" data-testid="command-palette">
      <button type="button" className="absolute inset-0 bg-black/40" aria-label="Закрыть" onClick={onClose} data-testid="command-palette-backdrop" />
      <div className="relative z-[101] w-full max-w-lg rounded-lg border bg-card p-2 shadow-lg">
        <div className="flex items-center gap-2 border-b px-2 pb-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border-0 shadow-none focus-visible:ring-0"
            placeholder="Поиск подключений, запусков, проблем, коннекторов…"
            data-testid="command-palette-input"
            autoFocus
          />
        </div>
        <ul className="max-h-72 overflow-auto py-1" role="listbox" aria-label="Результаты поиска">
          {filtered.map((it, idx) => (
            <li key={it.id}>
              <button
                type="button"
                className={cn("flex w-full flex-col items-start rounded-md px-3 py-2 text-left text-sm hover:bg-muted")}
                data-testid={`command-palette-item-${idx}`}
                onClick={() => {
                  setLocation(it.href);
                  onClose();
                }}
              >
                <span className="font-medium">{it.label}</span>
                <span className="text-xs text-muted-foreground">{it.hint}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="border-t px-3 py-2 text-[11px] text-muted-foreground">Ctrl+K — открыть · Esc — закрыть</p>
      </div>
    </div>
  );
}
