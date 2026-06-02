import type { IngestCatalogDto } from "@/lib/api-types";
import type { SchemaLayout, StreamDefaultDto, WizardColumnRuleRow } from "@/components/connection-wizard/wizard-types";
import { StepSchemaDiscover } from "@/components/connection-wizard/step-schema-discover";
import { ColumnRulesEditor } from "@/components/connection-wizard/column-rules-editor";
import { StreamReplicationModeEditor } from "@/components/stream-replication-mode-editor";

type Props = {
  layout: SchemaLayout;
  entityLabels: Record<string, string>;
  discovery: IngestCatalogDto | null;
  discoveryError: string | null;
  discovering: boolean;
  onDiscover: () => void;
  selectedEntities: string[];
  onToggleEntity: (name: string, enabled: boolean) => void;
  streamDefaults: StreamDefaultDto[];
  fieldNamesByStream: Record<string, string[]>;
  onChangeStreamDefault: (streamName: string, patch: Partial<StreamDefaultDto>) => void;
  columnRuleRows: WizardColumnRuleRow[];
  onChangeColumnRuleRow: (id: string, patch: Partial<WizardColumnRuleRow>) => void;
};

/**
 * Шаг 2 (в 4-шаговом мастере):
 * - обнаружение схемы + выбор сущностей (если layout=entities)
 * - режим передачи данных (дубликаты)
 * - правила нормализации колонок
 */
export function StepStreamsAndColumns({
  layout,
  entityLabels,
  discovery,
  discoveryError,
  discovering,
  onDiscover,
  selectedEntities,
  onToggleEntity,
  streamDefaults,
  fieldNamesByStream,
  onChangeStreamDefault,
  columnRuleRows,
  onChangeColumnRuleRow,
}: Props) {
  const activeStreams =
    layout === "flat"
      ? streamDefaults.filter((s) => discovery?.streams?.some((x) => x.name === s.stream_name))
      : streamDefaults.filter((s) => selectedEntities.includes(s.stream_name));

  return (
    <div className="space-y-4">
      <StepSchemaDiscover
        layout={layout}
        entityLabels={entityLabels}
        discovery={discovery}
        discoveryError={discoveryError}
        discovering={discovering}
        onDiscover={onDiscover}
        selectedEntities={selectedEntities}
        onToggleEntity={onToggleEntity}
      />

      {discovery ? (
        <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-replication-modes">
          <StreamReplicationModeEditor
            streams={activeStreams}
            fieldNamesByStream={fieldNamesByStream}
            onChangeStream={onChangeStreamDefault}
            testIdPrefix="wizard-replication"
          />
        </div>
      ) : null}

      <ColumnRulesEditor
        layout={layout}
        entityLabels={entityLabels}
        rows={columnRuleRows}
        onChangeRow={onChangeColumnRuleRow}
      />
    </div>
  );
}
