import type { IngestCatalogDto } from "@/lib/api-types";
import type { SelectedStreamCfg } from "@/components/connection-wizard/wizard-types";
import { Button } from "@/components/ui/button";

type Props = {
  discovery: IngestCatalogDto | null;
  discoveryError: string | null;
  discovering: boolean;
  onDiscover: () => void;
  enabledStreamNames: string[];
  streamOptions: Record<string, SelectedStreamCfg>;
  onToggleStream: (name: string, enabled: boolean) => void;
  onChangeStreamOption: (name: string, patch: Partial<SelectedStreamCfg>) => void;
};

export function StepDiscoverStreams({
  discovery,
  discoveryError,
  discovering,
  onDiscover,
  enabledStreamNames,
  streamOptions,
  onToggleStream,
  onChangeStreamOption,
}: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-discover-streams">
      <p className="mb-3 text-sm text-muted-foreground">
        Обнаружение потоков вызывает коннектор источника и возвращает доступные потоки и схемы полей.
      </p>
      <Button type="button" onClick={onDiscover} disabled={discovering} data-testid="button-discover-streams">
        {discovering ? "Обнаружение…" : "Обнаружить потоки"}
      </Button>
      {discoveryError ? (
        <p className="mt-3 text-sm text-destructive" data-testid="error-discover-streams">
          {discoveryError}
        </p>
      ) : null}

      {discovery?.streams?.length ? (
        <div className="mt-4 overflow-auto rounded-md border" data-testid="table-discovered-streams">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="p-2">Вкл.</th>
                <th className="p-2">Поток</th>
                <th className="p-2">Режим</th>
                <th className="p-2">Поле курсора (incremental)</th>
              </tr>
            </thead>
            <tbody>
              {discovery.streams.map((s) => {
                const enabled = enabledStreamNames.includes(s.name);
                const opt = streamOptions[s.name] ?? {
                  sync_mode: "full_refresh" as const,
                  cursor_field: null,
                };
                const modes = (
                  s.supported_sync_modes?.length ? s.supported_sync_modes : ["full_refresh", "incremental"]
                ) as ("full_refresh" | "incremental")[];
                const modeOpts = modes.length ? modes : (["full_refresh", "incremental"] as const);
                return (
                  <tr key={s.name} className="border-t" data-testid={`row-stream-${s.name}`}>
                    <td className="p-2">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => onToggleStream(s.name, e.target.checked)}
                        data-testid={`checkbox-stream-${s.name}`}
                        aria-label={`Включить поток ${s.name}`}
                      />
                    </td>
                    <td className="p-2 font-mono text-xs">{s.name}</td>
                    <td className="p-2">
                      <select
                        className="h-8 rounded-md border bg-background px-2 text-xs"
                        value={opt.sync_mode}
                        disabled={!enabled}
                        onChange={(e) =>
                          onChangeStreamOption(s.name, {
                            sync_mode: e.target.value as SelectedStreamCfg["sync_mode"],
                          })
                        }
                        data-testid={`select-sync-mode-${s.name}`}
                      >
                        {modeOpts.includes("full_refresh") ? <option value="full_refresh">full_refresh</option> : null}
                        {modeOpts.includes("incremental") ? <option value="incremental">incremental</option> : null}
                      </select>
                    </td>
                    <td className="p-2">
                      <input
                        className="h-8 w-full max-w-xs rounded-md border bg-background px-2 text-xs font-mono"
                        value={opt.cursor_field ?? ""}
                        disabled={!enabled || opt.sync_mode !== "incremental"}
                        placeholder={s.default_cursor_field?.[0] ?? "cursor"}
                        onChange={(e) => onChangeStreamOption(s.name, { cursor_field: e.target.value || null })}
                        data-testid={`input-cursor-field-${s.name}`}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground" data-testid="hint-no-streams">
          Сначала выполните обнаружение потоков.
        </p>
      )}
    </div>
  );
}
