import type { WizardMappingRow } from "@/components/connection-wizard/wizard-types";
import { StepMapping } from "@/components/connection-wizard/step-mapping";

type Props = {
  rows: WizardMappingRow[];
  onChangeRow: (id: string, patch: Partial<WizardMappingRow>) => void;
};

/**
 * Редактор правил колонок.
 *
 * Сейчас использует существующий StepMapping (таргеты и mandatory флаги),
 * чтобы не ломать текущую логику сохранения подключения.
 * В будущих PR этот компонент заменит select'ы на полноценный editor rules.
 */
export function ColumnRulesEditor({ rows, onChangeRow }: Props) {
  return <StepMapping rows={rows} onChangeRow={onChangeRow} />;
}

