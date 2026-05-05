import type { IngestCatalogDto } from "@/lib/api-types";
import type { SelectedStreamCfg, WizardMappingRow } from "@/components/connection-wizard/wizard-types";
import { StepDiscoverStreams } from "@/components/connection-wizard/step-discover-streams";
import { ColumnRulesEditor } from "@/components/connection-wizard/column-rules-editor";

type Props = {
  discovery: IngestCatalogDto | null;
  discoveryError: string | null;
  discovering: boolean;
  onDiscover: () => void;
  enabledStreamNames: string[];
  streamOptions: Record<string, SelectedStreamCfg>;
  onToggleStream: (name: string, enabled: boolean) => void;
  onChangeStreamOption: (name: string, patch: Partial<SelectedStreamCfg>) => void;
  mappingRows: WizardMappingRow[];
  onChangeMappingRow: (id: string, patch: Partial<WizardMappingRow>) => void;
};

/**
 * Шаг 2 (в 4-шаговом мастере):
 * - обнаружение потоков + настройка cursor/sync_mode
 * - редактор правил/маппинга колонок
 */
export function StepStreamsAndColumns({
  discovery,
  discoveryError,
  discovering,
  onDiscover,
  enabledStreamNames,
  streamOptions,
  onToggleStream,
  onChangeStreamOption,
  mappingRows,
  onChangeMappingRow,
}: Props) {
  return (
    <div className="space-y-4">
      <StepDiscoverStreams
        discovery={discovery}
        discoveryError={discoveryError}
        discovering={discovering}
        onDiscover={onDiscover}
        enabledStreamNames={enabledStreamNames}
        streamOptions={streamOptions}
        onToggleStream={onToggleStream}
        onChangeStreamOption={onChangeStreamOption}
      />
      <div>
        <ColumnRulesEditor rows={mappingRows} onChangeRow={onChangeMappingRow} />
      </div>
    </div>
  );
}

