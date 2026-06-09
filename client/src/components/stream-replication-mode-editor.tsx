import { useState } from "react";
import type { StreamDefaultDto } from "@/components/connection-wizard/wizard-types";
import {
  parseCursorFields,
  REPLICATION_PRESETS,
  fieldsFromReplicationPreset,
  parsePrimaryKeyFields,
  replicationPresetFromFields,
  suggestPrimaryKeyField,
  type ReplicationPresetId,
} from "@/lib/destination-sync-mode";

type Props = {
  streams: StreamDefaultDto[];
  /** Поля потока для подсказки PK / cursor */
  fieldNamesByStream: Record<string, string[]>;
  onChangeStream: (streamName: string, patch: Partial<StreamDefaultDto>) => void;
  testIdPrefix?: string;
};

export function StreamReplicationModeEditor({
  streams,
  fieldNamesByStream,
  onChangeStream,
  testIdPrefix = "replication",
}: Props) {
  const tid = (suffix: string) => `${testIdPrefix}-${suffix}`;
  const [pkSearchByStream, setPkSearchByStream] = useState<Record<string, string>>({});
  const [cursorSearchByStream, setCursorSearchByStream] = useState<Record<string, string>>({});

  if (streams.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid={tid("empty")}>
        Сначала обнаружьте схему и выберите сущности.
      </p>
    );
  }

  return (
    <div className="space-y-4" data-testid={tid("editor")}>
      <div>
        <p className="text-sm font-medium">Режим передачи данных</p>
      </div>
      {streams.map((st) => {
        const presetId = replicationPresetFromFields(st.sync_mode, st.destination_sync_mode);
        const preset = REPLICATION_PRESETS.find((p) => p.id === presetId)!;
        const fields = fieldNamesByStream[st.stream_name] ?? [];
        const search = (pkSearchByStream[st.stream_name] ?? "").trim().toLowerCase();
        const filteredFields = search
          ? fields.filter((f) => f.toLowerCase().includes(search))
          : fields;
        const selectedPrimaryKeys = st.primary_key ?? [];

        const setPreset = (id: ReplicationPresetId) => {
          const mapped = fieldsFromReplicationPreset(id);
          const patch: Partial<StreamDefaultDto> = {
            sync_mode: mapped.sync_mode,
            destination_sync_mode: mapped.destination_sync_mode,
          };
          const p = REPLICATION_PRESETS.find((x) => x.id === id)!;
          if (p.needsCursor && (st.cursor_field ?? []).length === 0) {
            patch.cursor_field = fields[0] ? [fields[0]] : [];
          }
          if (!p.needsCursor) {
            patch.cursor_field = null;
          }
          if (p.needsPrimaryKey && (st.primary_key ?? []).length === 0) {
            const suggested = suggestPrimaryKeyField(fields);
            patch.primary_key = suggested ? [suggested] : [];
          }
          if (!p.needsPrimaryKey) {
            patch.primary_key = null;
          }
          onChangeStream(st.stream_name, patch);
        };

        return (
          <div
            key={st.stream_name}
            className="rounded-md border bg-muted/20 p-3"
            data-testid={tid(`stream-${st.stream_name}`)}
          >
            <p className="mb-2 font-mono text-xs text-muted-foreground">{st.stream_name}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {REPLICATION_PRESETS.map((opt) => (
                <label
                  key={opt.id}
                  className={`flex cursor-pointer gap-2 rounded-md border p-2 text-sm ${
                    presetId === opt.id ? "border-primary bg-secondary/60" : "hover:bg-muted/50"
                  }`}
                >
                  <input
                    type="radio"
                    name={`${testIdPrefix}-mode-${st.stream_name}`}
                    className="mt-0.5"
                    checked={presetId === opt.id}
                    onChange={() => setPreset(opt.id)}
                    data-testid={tid(`radio-${st.stream_name}-${opt.id}`)}
                  />
                  <span>
                    <span className="font-medium">{opt.label}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">{opt.hint}</span>
                  </span>
                </label>
              ))}
            </div>

            {preset.needsCursor ? (
              <div className="mt-3">
                <label className="text-xs font-medium text-muted-foreground" htmlFor={tid(`cursor-${st.stream_name}`)}>
                  Поле курсора
                </label>
                {fields.length > 0 ? (
                  <div
                    id={tid(`cursor-${st.stream_name}`)}
                    className="mt-1 grid max-w-md gap-1 rounded-md border bg-background p-2"
                    data-testid={tid(`select-cursor-${st.stream_name}`)}
                  >
                    <input
                      className="mb-1 flex h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={cursorSearchByStream[st.stream_name] ?? ""}
                      onChange={(e) =>
                        setCursorSearchByStream((prev) => ({ ...prev, [st.stream_name]: e.target.value }))
                      }
                      placeholder="Поиск поля курсора"
                      data-testid={tid(`input-cursor-search-${st.stream_name}`)}
                    />
                    {(st.cursor_field ?? []).length > 0 ? (
                      <div className="mb-1 flex flex-wrap gap-1" data-testid={tid(`chips-cursor-${st.stream_name}`)}>
                        {(st.cursor_field ?? []).map((keyName) => (
                          <button
                            key={keyName}
                            type="button"
                            className="rounded-full border px-2 py-0.5 text-xs font-mono hover:bg-muted"
                            onClick={() =>
                              onChangeStream(st.stream_name, {
                                cursor_field: (st.cursor_field ?? []).filter((x) => x !== keyName),
                              })
                            }
                            data-testid={tid(`chip-cursor-${st.stream_name}-${keyName}`)}
                            title="Убрать поле курсора"
                          >
                            {keyName} ×
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {fields
                      .filter((f) => {
                        const q = (cursorSearchByStream[st.stream_name] ?? "").trim().toLowerCase();
                        return q ? f.toLowerCase().includes(q) : true;
                      })
                      .map((f) => {
                        const selected = (st.cursor_field ?? []).includes(f);
                        return (
                          <label key={f} className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={(e) => {
                                const next = new Set(st.cursor_field ?? []);
                                if (e.target.checked) next.add(f);
                                else next.delete(f);
                                onChangeStream(st.stream_name, { cursor_field: Array.from(next) });
                              }}
                              data-testid={tid(`checkbox-cursor-${st.stream_name}-${f}`)}
                            />
                            <span className="font-mono text-xs">{f}</span>
                          </label>
                        );
                      })}
                  </div>
                ) : (
                  <input
                    className="mt-1 flex h-9 w-full max-w-md rounded-md border bg-background px-2 font-mono text-sm"
                    value={(st.cursor_field ?? []).join(", ")}
                    onChange={(e) =>
                      onChangeStream(st.stream_name, { cursor_field: parseCursorFields(e.target.value) })
                    }
                    placeholder="updated_at, created_at"
                    data-testid={tid(`input-cursor-${st.stream_name}`)}
                  />
                )}
              </div>
            ) : null}

            {preset.needsPrimaryKey ? (
              <div className="mt-3">
                <label className="text-xs font-medium text-muted-foreground" htmlFor={tid(`pk-${st.stream_name}`)}>
                  Первичный ключ (дедупликация)
                </label>
                {fields.length > 0 ? (
                  <div
                    id={tid(`pk-${st.stream_name}`)}
                    className="mt-1 grid max-w-md gap-1 rounded-md border bg-background p-2"
                    data-testid={tid(`select-pk-${st.stream_name}`)}
                  >
                    <input
                      className="mb-1 flex h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={pkSearchByStream[st.stream_name] ?? ""}
                      onChange={(e) =>
                        setPkSearchByStream((prev) => ({ ...prev, [st.stream_name]: e.target.value }))
                      }
                      placeholder="Поиск поля (например, id)"
                      data-testid={tid(`input-pk-search-${st.stream_name}`)}
                    />
                    {selectedPrimaryKeys.length > 0 ? (
                      <div className="mb-1 flex flex-wrap gap-1" data-testid={tid(`chips-pk-${st.stream_name}`)}>
                        {selectedPrimaryKeys.map((keyName) => (
                          <button
                            key={keyName}
                            type="button"
                            className="rounded-full border px-2 py-0.5 text-xs font-mono hover:bg-muted"
                            onClick={() =>
                              onChangeStream(st.stream_name, {
                                primary_key: selectedPrimaryKeys.filter((x) => x !== keyName),
                              })
                            }
                            data-testid={tid(`chip-pk-${st.stream_name}-${keyName}`)}
                            title="Убрать из первичного ключа"
                          >
                            {keyName} ×
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {filteredFields.map((f) => {
                      const selected = selectedPrimaryKeys.includes(f);
                      return (
                        <label key={f} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={(e) => {
                              const next = new Set(selectedPrimaryKeys);
                              if (e.target.checked) next.add(f);
                              else next.delete(f);
                              onChangeStream(st.stream_name, { primary_key: Array.from(next) });
                            }}
                            data-testid={tid(`checkbox-pk-${st.stream_name}-${f}`)}
                          />
                          <span className="font-mono text-xs">{f}</span>
                        </label>
                      );
                    })}
                    {filteredFields.length === 0 ? (
                      <p className="text-xs text-muted-foreground" data-testid={tid(`pk-empty-${st.stream_name}`)}>
                        По запросу ничего не найдено.
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <input
                    className="mt-1 flex h-9 w-full max-w-md rounded-md border bg-background px-2 font-mono text-sm"
                    value={(st.primary_key ?? []).join(", ")}
                    onChange={(e) =>
                      onChangeStream(st.stream_name, {
                        primary_key: parsePrimaryKeyFields(e.target.value),
                      })
                    }
                    placeholder="id, tenant_id"
                    data-testid={tid(`input-pk-${st.stream_name}`)}
                  />
                )}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
