import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { ColumnRulesEditor } from "@/components/connection-wizard/column-rules-editor";
import { inferColumnRuleType } from "@/components/connection-wizard/infer-column-rule-type";
import { schemaPropertyKeys } from "@/components/connection-wizard/schema-utils";
import type { SchemaLayout, StreamDefaultDto, WizardColumnRuleRow } from "@/components/connection-wizard/wizard-types";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StreamReplicationModeEditor } from "@/components/stream-replication-mode-editor";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { patchEltConnection, postEltSourceDiscover } from "@/lib/api-elt";
import { formatApiErrorMessage } from "@/lib/api-client";
import type { IngestCatalogDto } from "@/lib/api-types";
import {
  buildConnectionStreamsPatchPayload,
  columnRulesDtoToWizardRows,
  detailStreamsToDefaults,
  discoverResponseToState,
  enabledStreamNames,
  layoutFromDetail,
  mergeStreamDefaultsWithDiscover,
} from "@/lib/connection-stream-config";
import { queryKeys } from "@/lib/query-keys";

function fieldNamesByStreamFromDiscovery(
  discovery: IngestCatalogDto | null,
  streamNames: string[],
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  if (!discovery) return out;
  for (const sn of streamNames) {
    const st = discovery.streams.find((s) => s.name === sn);
    if (!st) continue;
    out[sn] = schemaPropertyKeys(st.json_schema as Record<string, unknown> | undefined);
  }
  return out;
}

export function ConnectionStreamsEditPage() {
  const { connection, detail, id, workspaceCode, isLoading, isError } = useConnectionFromPath();
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();

  const [layout, setLayout] = useState<SchemaLayout>("flat");
  const [entityLabels, setEntityLabels] = useState<Record<string, string>>({});
  const [discovery, setDiscovery] = useState<IngestCatalogDto | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [streamDefaults, setStreamDefaults] = useState<StreamDefaultDto[]>([]);
  const [columnRuleRows, setColumnRuleRows] = useState<WizardColumnRuleRow[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!detail || initialized) return;
    const ly = layoutFromDetail(detail);
    setLayout(ly);
    const enabled = enabledStreamNames(detail);
    const defaults = detailStreamsToDefaults((detail.streams ?? []).filter((s) => s.is_enabled));
    setStreamDefaults(defaults.length ? defaults : detailStreamsToDefaults(detail.streams ?? []));
    const rules = detail.column_rules ?? [];
    if (rules.length) {
      setColumnRuleRows(columnRulesDtoToWizardRows(rules, ly));
    }
    setEntityLabels(
      detail.wizard_meta && typeof detail.wizard_meta === "object" && detail.wizard_meta.entity_labels
        ? (detail.wizard_meta.entity_labels as Record<string, string>)
        : {},
    );
    setInitialized(true);
    void postEltSourceDiscover(detail.source_id, workspaceCode)
      .then((resp) => {
        const st = discoverResponseToState(resp);
        setLayout(st.layout);
        setEntityLabels(st.entityLabels);
        setDiscovery(st.discovery);
        setDiscoveryError(null);
        const merged = mergeStreamDefaultsWithDiscover(
          detailStreamsToDefaults((detail.streams ?? []).filter((s) => s.is_enabled)),
          st.streamDefaults.filter((d) => enabled.includes(d.stream_name)),
        );
        setStreamDefaults(merged.length ? merged : st.streamDefaults.filter((d) => enabled.includes(d.stream_name)));
        if (!rules.length && st.discovery) {
          const keys = enabled.length ? enabled : st.discovery.streams.map((x) => x.name);
          const rows: WizardColumnRuleRow[] = [];
          for (const name of keys) {
            const stRow = st.discovery.streams.find((s) => s.name === name);
            if (!stRow) continue;
            const schema = stRow.json_schema as Record<string, unknown> | undefined;
            for (const k of schemaPropertyKeys(schema)) {
              rows.push({
                id: `${name}:${k}`,
                entity: st.layout === "entities" ? name : null,
                sourceField: k,
                targetField: k,
                ruleType: inferColumnRuleType(k),
                required: false,
              });
            }
          }
          if (rows.length) setColumnRuleRows(rows);
        }
      })
      .catch((e: unknown) => {
        setDiscoveryError(formatApiErrorMessage(e, "Не удалось обнаружить схему"));
      });
  }, [detail, initialized, workspaceCode]);

  const activeStreamNames = useMemo(() => {
    if (!detail) return [];
    return enabledStreamNames(detail);
  }, [detail]);

  const activeStreamDefaults = useMemo(
    () => streamDefaults.filter((s) => activeStreamNames.includes(s.stream_name)),
    [streamDefaults, activeStreamNames],
  );

  const fieldNamesByStream = useMemo(
    () => fieldNamesByStreamFromDiscovery(discovery, activeStreamNames),
    [discovery, activeStreamNames],
  );

  const saveMut = useMutation({
    mutationFn: async () => {
      if (!detail) throw new Error("Подключение не загружено");
      const body = buildConnectionStreamsPatchPayload({
        detail,
        streamDefaults,
        columnRuleRows,
        layout,
      });
      return patchEltConnection(Number(id), { workspace_code: workspaceCode, ...body });
    },
    onSuccess: () => {
      setErr(null);
      setSaveMsg("Настройки потоков сохранены. Запустите синхронизацию, чтобы применить изменения.");
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltDetail(id, workspaceCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.detail(id) });
    },
    onError: (e: unknown) => {
      setSaveMsg(null);
      setErr(formatApiErrorMessage(e, "Ошибка сохранения"));
    },
  });

  const onRediscover = async () => {
    if (!detail) return;
    setDiscoveryError(null);
    try {
      const resp = await postEltSourceDiscover(detail.source_id, workspaceCode);
      const st = discoverResponseToState(resp);
      setLayout(st.layout);
      setEntityLabels(st.entityLabels);
      setDiscovery(st.discovery);
      setStreamDefaults((prev) =>
        mergeStreamDefaultsWithDiscover(
          prev,
          st.streamDefaults.filter((d) => activeStreamNames.includes(d.stream_name)),
        ),
      );
    } catch (e: unknown) {
      setDiscoveryError(formatApiErrorMessage(e, "Ошибка обнаружения схемы"));
    }
  };

  const onChangeStreamDefault = (streamName: string, patch: Partial<StreamDefaultDto>) => {
    setStreamDefaults((prev) => prev.map((s) => (s.stream_name === streamName ? { ...s, ...patch } : s)));
  };

  const onChangeColumnRuleRow = (rowId: string, patch: Partial<WizardColumnRuleRow>) => {
    setColumnRuleRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, ...patch } : r)));
  };

  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection || !detail) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Редактирование потоков"
        description={`${connection.name} — режимы репликации и типы колонок`}
        breadcrumbs="Интеграции / Подключения / Потоки / Редактирование"
        actions={
          <LinkAsButton href={`/connections/${id}/streams`} variant="outline" data-testid="link-streams-edit-back">
            К просмотру потоков
          </LinkAsButton>
        }
      />
      <ConnectionSubNav connectionId={id} />

      <Card className="space-y-3 p-4" data-testid="connection-streams-edit-hint">
        <p className="text-sm text-muted-foreground">
          Измените типы полей (например, <code className="text-xs">STAGE_ID</code> → строка), сохраните и снова
          запустите синхронизацию. Пересоздавать подключение не нужно.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" data-testid="button-rediscover-streams" onClick={() => void onRediscover()}>
            Обновить схему из источника
          </Button>
        </div>
        {discoveryError ? (
          <p className="text-sm text-destructive" data-testid="text-streams-edit-discover-error">
            {discoveryError}
          </p>
        ) : null}
      </Card>

      {activeStreamDefaults.length > 0 ? (
        <Card className="p-4" data-testid="connection-streams-edit-replication">
          <StreamReplicationModeEditor
            streams={activeStreamDefaults}
            fieldNamesByStream={fieldNamesByStream}
            onChangeStream={onChangeStreamDefault}
            testIdPrefix="conn-edit-replication"
          />
        </Card>
      ) : (
        <p className="text-sm text-muted-foreground">Нет включённых потоков для редактирования.</p>
      )}

      <ColumnRulesEditor layout={layout} entityLabels={entityLabels} rows={columnRuleRows} onChangeRow={onChangeColumnRuleRow} />

      {saveMsg ? (
        <p className="text-sm text-muted-foreground" data-testid="text-streams-edit-saved">
          {saveMsg}
        </p>
      ) : null}
      {err ? (
        <p className="text-sm text-destructive" data-testid="text-streams-edit-error">
          {err}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          data-testid="button-save-streams-edit"
          disabled={saveMut.isPending || activeStreamDefaults.length === 0}
          onClick={() => saveMut.mutate()}
        >
          Сохранить настройки потоков
        </Button>
        <Button
          type="button"
          variant="outline"
          data-testid="button-save-and-go-runs"
          disabled={saveMut.isPending}
          onClick={() => {
            saveMut.mutate(undefined, {
              onSuccess: () => setLocation(`/connections/${id}/runs`),
            });
          }}
        >
          Сохранить и перейти к запускам
        </Button>
      </div>
    </div>
  );
}
