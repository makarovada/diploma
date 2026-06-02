import type { IngestCatalogDto } from "@/lib/api-types";
import type { SchemaLayout } from "@/components/connection-wizard/wizard-types";
import { Button } from "@/components/ui/button";

type Props = {
  layout: SchemaLayout;
  entityLabels: Record<string, string>;
  discovery: IngestCatalogDto | null;
  discoveryError: string | null;
  discovering: boolean;
  onDiscover: () => void;
  selectedEntities: string[];
  onToggleEntity: (name: string, enabled: boolean) => void;
};

export function StepSchemaDiscover({
  layout,
  entityLabels,
  discovery,
  discoveryError,
  discovering,
  onDiscover,
  selectedEntities,
  onToggleEntity,
}: Props) {
  const showEntityPicker = layout === "entities" && (discovery?.streams?.length ?? 0) > 0;

  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-schema-discover">
      <p className="mb-3 text-sm text-muted-foreground">
        {layout === "entities"
          ? "Обнаружение возвращает доступные сущности источника и поля их схемы. Выберите, какие сущности включить в подключение."
          : "Обнаружение возвращает поля источника. Задайте для каждого поля тип данных и правило нормализации."}
      </p>
      <Button type="button" onClick={onDiscover} disabled={discovering} data-testid="button-discover-columns">
        {discovering ? "Обнаружение…" : "Обнаружить колонки"}
      </Button>
      {discoveryError ? (
        <p className="mt-3 text-sm text-destructive" data-testid="error-discover-columns">
          {discoveryError}
        </p>
      ) : null}

      {showEntityPicker ? (
        <div className="mt-4 overflow-auto rounded-md border" data-testid="table-discovered-entities">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="p-2">Вкл.</th>
                <th className="p-2">Сущность</th>
                <th className="p-2">Код</th>
              </tr>
            </thead>
            <tbody>
              {discovery!.streams.map((s) => {
                const enabled = selectedEntities.includes(s.name);
                const label = entityLabels[s.name] ?? s.name;
                return (
                  <tr key={s.name} className="border-t" data-testid={`row-entity-${s.name}`}>
                    <td className="p-2">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => onToggleEntity(s.name, e.target.checked)}
                        data-testid={`checkbox-entity-${s.name}`}
                        aria-label={`Включить сущность ${label}`}
                      />
                    </td>
                    <td className="p-2">{label}</td>
                    <td className="p-2 font-mono text-xs text-muted-foreground">{s.name}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : discovery?.streams?.length ? (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="hint-schema-ready">
          Обнаружено полей:{" "}
          {discovery.streams.reduce((acc, s) => {
            const props = (s.json_schema as { properties?: Record<string, unknown> } | undefined)?.properties;
            return acc + (props ? Object.keys(props).length : 0);
          }, 0)}
        </p>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="hint-no-schema">
          Сначала выполните обнаружение колонок.
        </p>
      )}
    </div>
  );
}
