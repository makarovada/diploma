import type { EltSourceItemDto } from "@/lib/api-types";
import { LinkAsButton } from "@/components/link-as-button";

type Props = {
  sources: EltSourceItemDto[];
  sourceId: number | null;
  onSelectSourceId: (id: number | null) => void;
  loading: boolean;
  emptyHint?: string | null;
};

export function StepSource({ sources, sourceId, onSelectSourceId, loading, emptyHint }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-source">
      <p className="mb-3 text-sm text-muted-foreground">
        Выберите сохранённый источник данных. При необходимости сначала создайте источник в разделе «Источники».
      </p>
      {loading ? (
        <p className="text-sm text-muted-foreground" data-testid="wizard-sources-loading">
          Загрузка списка источников…
        </p>
      ) : sources.length === 0 ? (
        <div data-testid="wizard-sources-empty">
          <p className="text-sm text-muted-foreground">{emptyHint ?? "Нет доступных источников."}</p>
          <LinkAsButton href="/sources/new" className="mt-3" data-testid="link-create-source">
            Создать источник
          </LinkAsButton>
        </div>
      ) : (
        <div className="max-w-xl">
          <label className="text-sm font-medium" htmlFor="wizard-select-source">
            Источник <span className="text-destructive">*</span>
          </label>
          <select
            id="wizard-select-source"
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={sourceId ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onSelectSourceId(v ? Number(v) : null);
            }}
            data-testid="select-wizard-source"
          >
            <option value="">— выберите —</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.connector_code})
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
