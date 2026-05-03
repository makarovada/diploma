import type { EltDestinationItemDto } from "@/lib/api-types";
import { LinkAsButton } from "@/components/link-as-button";

type Props = {
  destinations: EltDestinationItemDto[];
  destinationId: number | null;
  onSelectDestinationId: (id: number | null) => void;
  loading: boolean;
};

export function StepDestination({ destinations, destinationId, onSelectDestinationId, loading }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-destination">
      <p className="mb-3 text-sm text-muted-foreground">
        Выберите приёмник данных (например PostgreSQL / склад). Создайте приёмник заранее при необходимости.
      </p>
      {loading ? (
        <p className="text-sm text-muted-foreground" data-testid="wizard-destinations-loading">
          Загрузка приёмников…
        </p>
      ) : destinations.length === 0 ? (
        <div data-testid="wizard-destinations-empty">
          <p className="text-sm text-muted-foreground">Нет доступных приёмников.</p>
          <LinkAsButton href="/destinations/new" className="mt-3" data-testid="link-create-destination">
            Создать приёмник
          </LinkAsButton>
        </div>
      ) : (
        <div className="max-w-xl">
          <label className="text-sm font-medium" htmlFor="wizard-select-destination">
            Приёмник <span className="text-destructive">*</span>
          </label>
          <select
            id="wizard-select-destination"
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={destinationId ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onSelectDestinationId(v ? Number(v) : null);
            }}
            data-testid="select-wizard-destination"
          >
            <option value="">— выберите —</option>
            {destinations.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.connector_code})
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
