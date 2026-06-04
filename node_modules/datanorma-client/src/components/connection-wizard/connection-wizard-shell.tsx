import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StepCheckDestination } from "@/components/connection-wizard/step-check-destination";
import { StepCheckSource } from "@/components/connection-wizard/step-check-source";
import { StepDestination } from "@/components/connection-wizard/step-destination";
import { StepName } from "@/components/connection-wizard/step-name";
import { StepStreamsAndColumns } from "@/components/connection-wizard/step-streams-and-columns";
import { StepReview } from "@/components/connection-wizard/step-review";
import { StepSaveRun } from "@/components/connection-wizard/step-save-run";
import { StepSchedule } from "@/components/connection-wizard/step-schedule";
import { StepSource } from "@/components/connection-wizard/step-source";
import { ConnectorConfigForm } from "@/components/connection-wizard/connector-config-form";
import { WIZARD_STEP_COUNT, WIZARD_STEP_LABELS } from "@/components/connection-wizard/wizard-constants";
import { jsonSchemaRequiredList, schemaPropertyKeys } from "@/components/connection-wizard/schema-utils";
import type {
  SchemaLayout,
  StreamDefaultDto,
  WizardColumnRuleRow,
  WizardFormState,
  WizardPersistMetaV2,
} from "@/components/connection-wizard/wizard-types";
import { inferColumnRuleType } from "@/components/connection-wizard/infer-column-rule-type";
import { stepBlocksNext } from "@/components/connection-wizard/wizard-validation";
import { Button } from "@/components/ui/button";
import {
  createEltConnection,
  fetchEltDestination,
  fetchEltDestinations,
  fetchEltSource,
  fetchEltSources,
  patchEltSource,
  postEltDestinationCheck,
  postEltSourceCheck,
  postEltSourceDiscover,
  triggerEltConnection,
} from "@/lib/api-elt";
import type { EltConnectionCreatePayload, EltDiscoverResponseDto, IngestCatalogDto } from "@/lib/api-types";
import { ApiError } from "@/lib/api-client";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import {
  encodeCursorFields,
  encodePrimaryKeyFields,
  parseCursorFields,
  parsePrimaryKeyFields,
} from "@/lib/destination-sync-mode";
import { queryKeys } from "@/lib/query-keys";
import {
  normalizeSourceConfigForConnector,
  normalizeSourceConfigTextForConnector,
} from "@/lib/source-config-normalize";
import {
  currentSpaReturnPath,
  hasGoogleOAuthCallback,
  OAUTH_WIZARD_RESTORE_KEY,
} from "@/lib/oauth-return";

function mergeColumnRules(next: WizardColumnRuleRow[], prev: WizardColumnRuleRow[]): WizardColumnRuleRow[] {
  const map = new Map(prev.map((r) => [r.id, r]));
  return next.map((r) => {
    const o = map.get(r.id);
    return o ? { ...r, targetField: o.targetField, ruleType: o.ruleType, required: o.required } : r;
  });
}

function buildColumnRulesFromDiscovery(
  discovery: IngestCatalogDto | null,
  layout: SchemaLayout,
  selectedKeys: string[],
): WizardColumnRuleRow[] {
  if (!discovery) return [];
  const rows: WizardColumnRuleRow[] = [];
  const keys = layout === "flat" ? (discovery.streams[0]?.name ? [discovery.streams[0].name] : []) : selectedKeys;
  for (const name of keys) {
    const st = discovery.streams.find((s) => s.name === name);
    if (!st) continue;
    const schema = st.json_schema as Record<string, unknown> | undefined;
    const propKeys = schemaPropertyKeys(schema);
    const req = new Set(jsonSchemaRequiredList(schema));
    for (const k of propKeys) {
      const id = `${name}:${k}`;
      rows.push({
        id,
        entity: layout === "entities" ? name : null,
        sourceField: k,
        targetField: k,
        ruleType: inferColumnRuleType(k),
        required: req.has(k),
      });
    }
  }
  return rows;
}

function activeStreamNames(form: WizardFormState): string[] {
  if (!form.discovery) return [];
  if (form.schemaLayout === "flat") {
    const n = form.discovery.streams[0]?.name;
    return n ? [n] : [];
  }
  return form.selectedEntities;
}

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

function buildStreamsPayload(form: WizardFormState): EltConnectionCreatePayload["streams"] {
  const keys =
    form.schemaLayout === "flat"
      ? form.discovery?.streams?.[0]?.name
        ? [form.discovery.streams[0].name]
        : []
      : form.selectedEntities;
  const defaultsByName = new Map(form.streamDefaults.map((d) => [d.stream_name, d]));
  return keys.map((sn) => {
    const d = defaultsByName.get(sn);
    const sync_mode = (d?.sync_mode ?? "full_refresh") as "full_refresh" | "incremental";
    return {
      stream_name: sn,
      sync_mode,
      destination_sync_mode: d?.destination_sync_mode ?? "refresh_overwrite",
      cursor_field: encodeCursorFields(d?.cursor_field),
      primary_key: encodePrimaryKeyFields(d?.primary_key),
      is_enabled: true,
    };
  });
}

function errMessage(e: unknown): string {
  if (e instanceof ApiError) {
    try {
      const j = JSON.parse(e.body) as { detail?: unknown };
      const d = j.detail;
      if (typeof d === "object" && d !== null) {
        if ("error_message" in d && typeof (d as { error_message: string }).error_message === "string") {
          return (d as { error_message: string }).error_message;
        }
        if ("message" in d && typeof (d as { message: string }).message === "string") {
          return (d as { message: string }).message;
        }
      }
    } catch {
      /* ignore */
    }
    return e.message || `HTTP ${e.status}`;
  }
  if (e instanceof Error) return e.message;
  return "Неизвестная ошибка";
}

const initialForm = (): WizardFormState => ({
  workspaceCode: "main",
  connectionName: "",
  connectionDescription: "",
  sourceId: null,
  credentialsConfigText: "{}",
  credentialsSavedText: null,
  sourceCheck: null,
  destinationCheck: null,
  discovery: null,
  discoveryError: null,
  schemaLayout: "flat",
  entityLabels: {},
  streamDefaults: [],
  selectedEntities: [],
  destinationId: null,
  columnRuleRows: [],
  normalizationEnabled: true,
  scheduleCron: "",
  timezone: "UTC",
  preflightOk: null,
  preflightMessage: null,
});

export function ConnectionWizardShell() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<WizardFormState>(initialForm);

  const [saveCredError, setSaveCredError] = useState<string | null>(null);
  const [checkSrcErr, setCheckSrcErr] = useState<string | null>(null);
  const [checkDstErr, setCheckDstErr] = useState<string | null>(null);
  const [submitErr, setSubmitErr] = useState<string | null>(null);
  const [doneMsg, setDoneMsg] = useState<string | null>(null);
  const [preflightRunning, setPreflightRunning] = useState(false);
  const [saveAction, setSaveAction] = useState<"save" | "run" | null>(null);

  const wsAppliedRef = useRef(false);
  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });

  useEffect(() => {
    if (wsAppliedRef.current) return;
    const items = wsQuery.data?.items;
    if (items?.length) {
      wsAppliedRef.current = true;
      const code = items[0].workspace_code;
      setForm((f) => ({ ...f, workspaceCode: code }));
    }
  }, [wsQuery.data?.items]);

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, "");
    const qs = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs || window.location.search.replace(/^\?/, ""));
    const s = sp.get("source");
    if (s && /^\d+$/.test(s)) {
      setForm((f) => ({ ...f, sourceId: Number(s) }));
    }
  }, []);

  useEffect(() => {
    if (!hasGoogleOAuthCallback()) return;
    try {
      const raw = sessionStorage.getItem(OAUTH_WIZARD_RESTORE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as {
        form?: WizardFormState;
        step?: number;
        returnPath?: string;
      };
      sessionStorage.removeItem(OAUTH_WIZARD_RESTORE_KEY);
      const target = saved.returnPath?.trim() || currentSpaReturnPath();
      if (target.startsWith("/connections/new")) {
        const pathOnly = target.split("?")[0];
        setLocation(pathOnly);
      }
      if (saved.form) setForm(saved.form);
      if (typeof saved.step === "number") setStep(saved.step);
    } catch {
      /* ignore */
    }
  }, [setLocation]);

  const sourcesQuery = useQuery({
    queryKey: [...queryKeys.sources.list(), "elt", form.workspaceCode],
    queryFn: () => fetchEltSources(form.workspaceCode),
  });

  const destQuery = useQuery({
    queryKey: [...queryKeys.destinations.list(), "elt", form.workspaceCode],
    queryFn: () => fetchEltDestinations(form.workspaceCode),
  });

  const sources = sourcesQuery.data?.items ?? [];
  const destinations = destQuery.data?.items ?? [];

  const sourceLabel = useMemo(() => {
    if (!form.sourceId) return "—";
    const s = sources.find((x) => x.id === form.sourceId);
    return s ? `${s.name} (#${s.id})` : `#${form.sourceId}`;
  }, [form.sourceId, sources]);

  const selectedSourceConnector = useMemo(() => {
    if (!form.sourceId) return null;
    const s = sources.find((x) => x.id === form.sourceId);
    return s?.connector_code ?? null;
  }, [form.sourceId, sources]);

  const destinationLabel = useMemo(() => {
    if (!form.destinationId) return "—";
    const d = destinations.find((x) => x.id === form.destinationId);
    return d ? `${d.name} (#${d.id})` : `#${form.destinationId}`;
  }, [form.destinationId, destinations]);

  useEffect(() => {
    if (!form.sourceId) return;
    if (hasGoogleOAuthCallback()) return;
    let cancelled = false;
    fetchEltSource(form.sourceId, form.workspaceCode)
      .then(({ item }) => {
        if (!cancelled) {
          const configText = normalizeSourceConfigTextForConnector(
            item.connector_code,
            JSON.stringify(item.config ?? {}, null, 2),
          );
          setForm((f) => ({
            ...f,
            credentialsConfigText: configText,
          }));
        }
      })
      .catch(() => {
        /* ignore — пользователь может править JSON вручную */
      });
    return () => {
      cancelled = true;
    };
  }, [form.sourceId, form.workspaceCode]);

  useEffect(() => {
    setForm((f) => ({
      ...f,
      credentialsSavedText: null,
      sourceCheck: null,
      destinationCheck: null,
      discovery: null,
      discoveryError: null,
      schemaLayout: "flat",
      entityLabels: {},
      streamDefaults: [],
      selectedEntities: [],
      columnRuleRows: [],
    }));
  }, [form.sourceId]);

  useEffect(() => {
    setForm((f) => ({ ...f, destinationCheck: null }));
  }, [form.destinationId]);

  useEffect(() => {
    if (step !== 1 || !form.discovery) return;
    const keys =
      form.schemaLayout === "flat"
        ? form.discovery.streams[0]?.name
          ? [form.discovery.streams[0].name]
          : []
        : form.selectedEntities;
    const built = buildColumnRulesFromDiscovery(form.discovery, form.schemaLayout, keys);
    setForm((f) => ({
      ...f,
      columnRuleRows: mergeColumnRules(built, f.columnRuleRows),
    }));
  }, [step, form.discovery, form.schemaLayout, form.selectedEntities]);

  useEffect(() => {
    if (!form.discovery) return;
    const keys = activeStreamNames(form);
    if (keys.length === 0) return;
    setForm((f) => {
      const byName = new Map(f.streamDefaults.map((d) => [d.stream_name, d]));
      const apiDefaults = new Map(f.streamDefaults.map((d) => [d.stream_name, d]));
      const next: StreamDefaultDto[] = keys.map((sn) => {
        const existing = byName.get(sn);
        if (existing) return existing;
        const fromApi = apiDefaults.get(sn);
        return {
          stream_name: sn,
          sync_mode: fromApi?.sync_mode ?? "full_refresh",
          destination_sync_mode: fromApi?.destination_sync_mode ?? "refresh_overwrite",
          cursor_field: fromApi?.cursor_field ? parseCursorFields(fromApi.cursor_field as string | string[] | null) : null,
          primary_key: fromApi?.primary_key ?? null,
        };
      });
      return { ...f, streamDefaults: next };
    });
  }, [form.discovery, form.schemaLayout, form.selectedEntities]);

  const replicationFieldNames = useMemo(
    () => fieldNamesByStreamFromDiscovery(form.discovery, activeStreamNames(form)),
    [form.discovery, form.schemaLayout, form.selectedEntities],
  );

  const onChangeStreamDefault = useCallback((streamName: string, patch: Partial<StreamDefaultDto>) => {
    setForm((f) => ({
      ...f,
      streamDefaults: f.streamDefaults.map((d) =>
        d.stream_name === streamName ? { ...d, ...patch } : d,
      ),
    }));
  }, []);

  useEffect(() => {
    if (step !== 3 || !form.sourceId || !form.destinationId) return;
    let cancelled = false;
    setPreflightRunning(true);
    setForm((f) => ({ ...f, preflightOk: null, preflightMessage: null }));
    Promise.all([fetchEltSource(form.sourceId!, form.workspaceCode), fetchEltDestination(form.destinationId!, form.workspaceCode)])
      .then(() => {
        if (!cancelled) {
          setForm((f) => ({
            ...f,
            preflightOk: true,
            preflightMessage: "Источник и приёмник найдены в workspace.",
          }));
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setForm((f) => ({
            ...f,
            preflightOk: false,
            preflightMessage: errMessage(e),
          }));
        }
      })
      .finally(() => {
        if (!cancelled) setPreflightRunning(false);
      });
    return () => {
      cancelled = true;
    };
  }, [step, form.sourceId, form.destinationId, form.workspaceCode]);

  const patchCfgMutation = useMutation({
    mutationFn: async (p: { sourceId: number; workspaceCode: string; configText: string }) => {
      const parsed = JSON.parse(p.configText || "{}") as Record<string, unknown>;
      const source = sources.find((x) => x.id === p.sourceId);
      const cfg = normalizeSourceConfigForConnector(source?.connector_code ?? null, parsed);
      return patchEltSource(p.sourceId, {
        workspace_code: p.workspaceCode,
        config: cfg,
      });
    },
  });

  const checkSrcMutation = useMutation({
    mutationFn: (p: { sourceId: number; workspaceCode: string }) => postEltSourceCheck(p.sourceId, p.workspaceCode),
  });

  const discoverMutation = useMutation({
    mutationFn: (p: { sourceId: number; workspaceCode: string }) => postEltSourceDiscover(p.sourceId, p.workspaceCode),
  });

  const checkDstMutation = useMutation({
    mutationFn: (p: { destinationId: number; workspaceCode: string }) =>
      postEltDestinationCheck(p.destinationId, p.workspaceCode),
  });

  type SaveMutPayload = {
    runAfter: boolean;
    form: WizardFormState;
  };

  const saveConnectionMutation = useMutation({
    mutationFn: async ({ runAfter, form: wf }: SaveMutPayload) => {
      const selected_entities =
        wf.schemaLayout === "flat"
          ? wf.discovery?.streams?.[0]?.name
            ? [wf.discovery.streams[0].name]
            : []
          : wf.selectedEntities;
      const meta: WizardPersistMetaV2 = {
        v: 2,
        layout: wf.schemaLayout,
        selected_entities,
        normalization_enabled: wf.normalizationEnabled,
        column_rules: wf.columnRuleRows.map((r) => ({
          entity: r.entity,
          source_field: r.sourceField,
          target_field: r.targetField.trim() || r.sourceField,
          type: r.ruleType,
          required: r.required,
        })),
      };
      const cron = wf.scheduleCron.trim() ? wf.scheduleCron.trim() : null;
      const column_rules = meta.column_rules.map((r) => ({
        entity: r.entity,
        source_field: r.source_field,
        target_field: r.target_field,
        type: r.type,
        required: r.required,
      }));
      const { item } = await createEltConnection({
        workspace_code: wf.workspaceCode,
        name: wf.connectionName.trim(),
        description: wf.connectionDescription.trim() || null,
        source_id: wf.sourceId!,
        destination_id: wf.destinationId!,
        schedule_cron: cron,
        timezone: wf.timezone || "UTC",
        streams: buildStreamsPayload(wf),
        column_rules,
        wizard_meta: meta,
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.connections.list() });
      await queryClient.invalidateQueries({ queryKey: ["connections", "elt"] });
      await queryClient.invalidateQueries({ queryKey: ["schedules", "v1"] });
      await queryClient.invalidateQueries({ queryKey: ["sources", "elt"] });
      if (!runAfter) {
        return { connectionId: item.id, runId: null as number | null };
      }
      try {
        const tr = await triggerEltConnection(item.id, wf.workspaceCode);
        return { connectionId: item.id, runId: tr.run_id };
      } catch (e) {
        return { connectionId: item.id, runId: null as number | null, triggerError: errMessage(e) };
      }
    },
    onSettled: () => setSaveAction(null),
  });

  const updateForm = useCallback((patch: Partial<WizardFormState>) => {
    setForm((f) => ({ ...f, ...patch }));
  }, []);

  const blocked = stepBlocksNext(step, form);
  const busyNav =
    patchCfgMutation.isPending ||
    checkSrcMutation.isPending ||
    discoverMutation.isPending ||
    checkDstMutation.isPending;

  const goNext = () => {
    if (step === 2) {
      setForm((f) => ({ ...f, preflightOk: null, preflightMessage: null }));
    }
    if (blocked || busyNav) return;
    setStep((s) => Math.min(WIZARD_STEP_COUNT - 1, s + 1));
  };

  const goBack = () => {
    setStep((s) => Math.max(0, s - 1));
    setSubmitErr(null);
  };

  const onSaveCredentials = async () => {
    setSaveCredError(null);
    if (!form.sourceId) {
      setSaveCredError("Не выбран источник.");
      return;
    }
    try {
      await patchCfgMutation.mutateAsync({
        sourceId: form.sourceId,
        workspaceCode: form.workspaceCode,
        configText: form.credentialsConfigText,
      });
      setForm((f) => ({ ...f, credentialsSavedText: f.credentialsConfigText }));
    } catch (e) {
      setSaveCredError(errMessage(e));
    }
  };

  const onRunSourceCheck = async () => {
    setCheckSrcErr(null);
    if (!form.sourceId) return;
    try {
      const r = await checkSrcMutation.mutateAsync({
        sourceId: form.sourceId,
        workspaceCode: form.workspaceCode,
      });
      setForm((f) => ({
        ...f,
        sourceCheck: { ok: r.ok, message: r.message },
      }));
    } catch (e) {
      setCheckSrcErr(errMessage(e));
      setForm((f) => ({ ...f, sourceCheck: null }));
    }
  };

  const onDiscover = async () => {
    setForm((f) => ({ ...f, discoveryError: null }));
    if (!form.sourceId) return;
    try {
      const resp = await discoverMutation.mutateAsync({
        sourceId: form.sourceId,
        workspaceCode: form.workspaceCode,
      });
      const layout = (resp.layout ?? "flat") as SchemaLayout;
      const entityLabels = resp.entity_labels ?? {};
      const streamDefaults = (resp.stream_defaults ?? []) as StreamDefaultDto[];
      const normalizedStreamDefaults: StreamDefaultDto[] = streamDefaults.map((d) => ({
        ...d,
        cursor_field: parseCursorFields(d.cursor_field as string | string[] | null),
        primary_key: parsePrimaryKeyFields(d.primary_key as string | string[] | null),
      }));
      const catalog = resp.catalog;
      const selectedEntities = layout === "entities" ? catalog.streams.map((x) => x.name) : [];
      setForm((f) => ({
        ...f,
        discovery: catalog,
        discoveryError: null,
        schemaLayout: layout,
        entityLabels,
        streamDefaults: normalizedStreamDefaults,
        selectedEntities,
      }));
    } catch (e) {
      setForm((f) => ({
        ...f,
        discovery: null,
        discoveryError: errMessage(e),
      }));
    }
  };

  const onToggleEntity = (name: string, enabled: boolean) => {
    setForm((f) => {
      const set = new Set(f.selectedEntities);
      if (enabled) set.add(name);
      else set.delete(name);
      return { ...f, selectedEntities: Array.from(set) };
    });
  };

  const onRunDestCheck = async () => {
    setCheckDstErr(null);
    if (!form.destinationId) return;
    try {
      const r = await checkDstMutation.mutateAsync({
        destinationId: form.destinationId,
        workspaceCode: form.workspaceCode,
      });
      setForm((f) => ({
        ...f,
        destinationCheck: { ok: r.ok, message: r.message },
      }));
    } catch (e) {
      setCheckDstErr(errMessage(e));
      setForm((f) => ({ ...f, destinationCheck: null }));
    }
  };

  const onSaveOnly = () => {
    setSubmitErr(null);
    setDoneMsg(null);
    setSaveAction("save");
    saveConnectionMutation.mutate(
      { runAfter: false, form },
      {
        onSuccess: (res) => {
          setDoneMsg(`Подключение создано (id ${res.connectionId}).`);
        },
        onError: (e) => setSubmitErr(errMessage(e)),
      },
    );
  };

  const onSaveAndRun = () => {
    setSubmitErr(null);
    setDoneMsg(null);
    setSaveAction("run");
    saveConnectionMutation.mutate(
      { runAfter: true, form },
      {
        onSuccess: (res) => {
          const extra = (res as { triggerError?: string }).triggerError;
          if (res.runId != null) {
            setDoneMsg(`Подключение id ${res.connectionId}, запуск #${res.runId}.`);
            setLocation(`/runs/${res.runId}`);
            return;
          }
          setDoneMsg(
            extra
              ? `Подключение id ${res.connectionId}. Запуск не выполнен: ${extra}`
              : `Подключение id ${res.connectionId}. Запуск недоступен или не удался — откройте карточку подключения.`,
          );
        },
        onError: (e) => setSubmitErr(errMessage(e)),
      },
    );
  };

  const onChangeColumnRuleRow = (id: string, patch: Partial<WizardColumnRuleRow>) => {
    setForm((f) => ({
      ...f,
      columnRuleRows: f.columnRuleRows.map((r) => (r.id === id ? { ...r, ...patch } : r)),
    }));
  };

  return (
    <div className="p-4">
      <PageHeader
        title="Мастер создания подключения"
        description="Пошаговая настройка интеграции (источник → приёмник → запуск)"
        breadcrumbs="Интеграции / Подключения / Новый сценарий"
      />

      <div className="mb-4 grid gap-2 md:grid-cols-4 lg:grid-cols-6" data-testid="wizard-stepper">
        {WIZARD_STEP_LABELS.map((label, i) => (
          <button
            key={label}
            type="button"
            className={`rounded-md border px-3 py-2 text-left text-sm ${i === step ? "bg-secondary" : ""}`}
            onClick={() => setStep(i)}
            data-testid={`wizard-step-${i + 1}`}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-4">
          <StepName
            name={form.connectionName}
            description={form.connectionDescription}
            onChange={(p) => updateForm(p)}
            nameError={null}
          />

          <StepSource
            sources={sources}
            sourceId={form.sourceId}
            onSelectSourceId={(id) => updateForm({ sourceId: id })}
            loading={sourcesQuery.isPending}
            emptyHint={sourcesQuery.isError ? "Не удалось загрузить источники (проверьте права и API)." : null}
          />

          <ConnectorConfigForm
            connectorCode={selectedSourceConnector}
            configText={form.credentialsConfigText}
            needsPersist={form.credentialsSavedText !== form.credentialsConfigText}
            onChangeText={(credentialsConfigText) => updateForm({ credentialsConfigText })}
            onSaveConfig={onSaveCredentials}
            onBeforeGoogleOAuth={() => {
              sessionStorage.setItem(
                OAUTH_WIZARD_RESTORE_KEY,
                JSON.stringify({ form, step, returnPath: currentSpaReturnPath() }),
              );
            }}
            saving={patchCfgMutation.isPending}
            saveError={saveCredError}
          />

          <StepCheckSource
            check={form.sourceCheck}
            checking={checkSrcMutation.isPending}
            onRunCheck={onRunSourceCheck}
            checkError={checkSrcErr}
          />
        </div>
      )}

      {step === 1 && (
        <StepStreamsAndColumns
          layout={form.schemaLayout}
          entityLabels={form.entityLabels}
          discovery={form.discovery}
          discoveryError={form.discoveryError}
          discovering={discoverMutation.isPending}
          onDiscover={onDiscover}
          selectedEntities={form.selectedEntities}
          onToggleEntity={onToggleEntity}
          streamDefaults={form.streamDefaults}
          fieldNamesByStream={replicationFieldNames}
          onChangeStreamDefault={onChangeStreamDefault}
          columnRuleRows={form.columnRuleRows}
          onChangeColumnRuleRow={onChangeColumnRuleRow}
        />
      )}

      {step === 2 && (
        <div className="space-y-4">
          <StepDestination
            destinations={destinations}
            destinationId={form.destinationId}
            onSelectDestinationId={(id) => updateForm({ destinationId: id })}
            loading={destQuery.isPending}
          />

          <StepCheckDestination
            check={form.destinationCheck}
            checking={checkDstMutation.isPending}
            onRunCheck={onRunDestCheck}
            checkError={checkDstErr}
          />
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <StepSchedule cron={form.scheduleCron} timezone={form.timezone} onChange={(p) => updateForm(p)} />

          <StepReview
            form={form}
            sourceLabel={sourceLabel}
            destinationLabel={destinationLabel}
            preflightRunning={preflightRunning}
          />

          <StepSaveRun
            saving={saveConnectionMutation.isPending && saveAction === "save"}
            triggering={saveConnectionMutation.isPending && saveAction === "run"}
            saveError={submitErr}
            doneMessage={doneMsg}
            onSaveOnly={onSaveOnly}
            onSaveAndRun={onSaveAndRun}
          />
        </div>
      )}

      <div className="mt-4 flex justify-between">
        <Button type="button" variant="outline" onClick={goBack} disabled={step === 0 || saveConnectionMutation.isPending} data-testid="button-step-back">
          Назад
        </Button>
        {step < WIZARD_STEP_COUNT - 1 ? (
          <Button
            type="button"
            onClick={goNext}
            disabled={blocked || busyNav}
            data-testid="button-step-next"
          >
            Далее
          </Button>
        ) : null}
      </div>
    </div>
  );
}
