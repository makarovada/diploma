import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "wouter";
import { PageHeader } from "@/components/page-header";
import { StepCheckDestination } from "@/components/connection-wizard/step-check-destination";
import { StepCheckSource } from "@/components/connection-wizard/step-check-source";
import { StepDestination } from "@/components/connection-wizard/step-destination";
import { StepDiscoverStreams } from "@/components/connection-wizard/step-discover-streams";
import { StepMapping } from "@/components/connection-wizard/step-mapping";
import { StepName } from "@/components/connection-wizard/step-name";
import { StepNormalization } from "@/components/connection-wizard/step-normalization";
import { StepReview } from "@/components/connection-wizard/step-review";
import { StepSaveRun } from "@/components/connection-wizard/step-save-run";
import { StepSchedule } from "@/components/connection-wizard/step-schedule";
import { StepSource } from "@/components/connection-wizard/step-source";
import { StepSourceCredentials } from "@/components/connection-wizard/step-source-credentials";
import { WIZARD_STEP_COUNT, WIZARD_STEP_LABELS } from "@/components/connection-wizard/wizard-constants";
import { jsonSchemaRequiredList, schemaPropertyKeys } from "@/components/connection-wizard/schema-utils";
import type {
  SelectedStreamCfg,
  WizardFormState,
  WizardMappingRow,
  WizardPersistMetaV1,
} from "@/components/connection-wizard/wizard-types";
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
import type { IngestCatalogDto } from "@/lib/api-types";
import { ApiError } from "@/lib/api-client";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

function embedWizardMetaInDescription(userText: string, meta: WizardPersistMetaV1): string {
  try {
    const json = JSON.stringify(meta);
    const suffix = `\n\n__DATANORMA_WIZARD__:${json}`;
    const base = userText.trim() || "Подключение создано мастером.";
    const max = 3990;
    if (base.length + suffix.length <= max) return base + suffix;
    return base.slice(0, Math.max(0, max - suffix.length)) + suffix;
  } catch {
    return userText.trim() || "Подключение создано мастером.";
  }
}

function mergeMappingTargets(next: WizardMappingRow[], prev: WizardMappingRow[]): WizardMappingRow[] {
  const map = new Map(prev.map((r) => [r.id, r]));
  return next.map((r) => {
    const o = map.get(r.id);
    return o ? { ...r, targetField: o.targetField, transformation: o.transformation } : r;
  });
}

function buildMappingRowsFromDiscovery(discovery: IngestCatalogDto | null, enabledNames: string[]): WizardMappingRow[] {
  if (!discovery) return [];
  const rows: WizardMappingRow[] = [];
  for (const name of enabledNames) {
    const st = discovery.streams.find((s) => s.name === name);
    if (!st) continue;
    const schema = st.json_schema as Record<string, unknown> | undefined;
    const keys = schemaPropertyKeys(schema);
    const req = new Set(jsonSchemaRequiredList(schema));
    for (const k of keys) {
      const id = `${name}:${k}`;
      rows.push({
        id,
        streamName: name,
        sourceField: k,
        targetField: "",
        transformation: "",
        required: req.has(k),
      });
    }
  }
  return rows;
}

function errMessage(e: unknown): string {
  if (e instanceof ApiError) {
    try {
      const j = JSON.parse(e.body) as { detail?: unknown };
      const d = j.detail;
      if (typeof d === "object" && d !== null && "message" in d && typeof (d as { message: string }).message === "string") {
        return (d as { message: string }).message;
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
  enabledStreamNames: [],
  streamOptions: {},
  destinationId: null,
  mappingRows: [],
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
    const sp = new URLSearchParams(window.location.search);
    const s = sp.get("source");
    if (s && /^\d+$/.test(s)) {
      setForm((f) => ({ ...f, sourceId: Number(s) }));
    }
  }, []);

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

  const destinationLabel = useMemo(() => {
    if (!form.destinationId) return "—";
    const d = destinations.find((x) => x.id === form.destinationId);
    return d ? `${d.name} (#${d.id})` : `#${form.destinationId}`;
  }, [form.destinationId, destinations]);

  useEffect(() => {
    if (!form.sourceId) return;
    let cancelled = false;
    fetchEltSource(form.sourceId, form.workspaceCode)
      .then(({ item }) => {
        if (!cancelled) {
          setForm((f) => ({
            ...f,
            credentialsConfigText: JSON.stringify(item.config ?? {}, null, 2),
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
      enabledStreamNames: [],
      streamOptions: {},
      mappingRows: [],
    }));
  }, [form.sourceId]);

  useEffect(() => {
    setForm((f) => ({ ...f, destinationCheck: null }));
  }, [form.destinationId]);

  useEffect(() => {
    if (step !== 7 || !form.discovery) return;
    const built = buildMappingRowsFromDiscovery(form.discovery, form.enabledStreamNames);
    setForm((f) => ({
      ...f,
      mappingRows: mergeMappingTargets(built, f.mappingRows),
    }));
  }, [step, form.discovery, form.enabledStreamNames]);

  useEffect(() => {
    if (step !== 10 || !form.sourceId || !form.destinationId) return;
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
      const cfg = JSON.parse(p.configText || "{}") as Record<string, unknown>;
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
      const meta: WizardPersistMetaV1 = {
        v: 1,
        normalization_enabled: wf.normalizationEnabled,
        mapping: wf.mappingRows.map((r) => ({
          stream: r.streamName,
          source_field: r.sourceField,
          target_field: r.targetField,
          transformation: r.transformation,
        })),
      };
      const description = embedWizardMetaInDescription(wf.connectionDescription, meta);
      const cron = wf.scheduleCron.trim() ? wf.scheduleCron.trim() : null;
      const { item } = await createEltConnection({
        workspace_code: wf.workspaceCode,
        name: wf.connectionName.trim(),
        description,
        source_id: wf.sourceId!,
        destination_id: wf.destinationId!,
        schedule_cron: cron,
        timezone: wf.timezone || "UTC",
        streams: wf.enabledStreamNames.map((sn) => {
          const o = wf.streamOptions[sn] ?? { sync_mode: "full_refresh" as const, cursor_field: null };
          return {
            stream_name: sn,
            sync_mode: o.sync_mode,
            cursor_field: o.sync_mode === "incremental" ? o.cursor_field : null,
            is_enabled: true,
          };
        }),
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.connections.list() });
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
    if (step === 9) {
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
      const { catalog } = await discoverMutation.mutateAsync({
        sourceId: form.sourceId,
        workspaceCode: form.workspaceCode,
      });
      const opts: Record<string, SelectedStreamCfg> = {};
      for (const s of catalog.streams) {
        const modes = s.supported_sync_modes?.length ? s.supported_sync_modes : ["full_refresh", "incremental"];
        let mode: SelectedStreamCfg["sync_mode"] = "full_refresh";
        if (modes.includes("incremental")) mode = "incremental";
        else if (modes.includes("full_refresh")) mode = "full_refresh";
        opts[s.name] = {
          sync_mode: mode,
          cursor_field: s.default_cursor_field?.[0] ?? null,
        };
      }
      setForm((f) => ({
        ...f,
        discovery: catalog,
        discoveryError: null,
        enabledStreamNames: catalog.streams.map((x) => x.name),
        streamOptions: opts,
      }));
    } catch (e) {
      setForm((f) => ({
        ...f,
        discovery: null,
        discoveryError: errMessage(e),
      }));
    }
  };

  const onToggleStream = (name: string, enabled: boolean) => {
    setForm((f) => {
      const set = new Set(f.enabledStreamNames);
      if (enabled) set.add(name);
      else set.delete(name);
      return { ...f, enabledStreamNames: Array.from(set) };
    });
  };

  const onChangeStreamOption = (name: string, patch: Partial<SelectedStreamCfg>) => {
    setForm((f) => {
      const cur = f.streamOptions[name] ?? { sync_mode: "full_refresh" as const, cursor_field: null };
      return {
        ...f,
        streamOptions: {
          ...f.streamOptions,
          [name]: { ...cur, ...patch },
        },
      };
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

  const onChangeMappingRow = (id: string, patch: Partial<WizardMappingRow>) => {
    setForm((f) => ({
      ...f,
      mappingRows: f.mappingRows.map((r) => (r.id === id ? { ...r, ...patch } : r)),
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
        <StepName
          name={form.connectionName}
          description={form.connectionDescription}
          onChange={(p) => updateForm(p)}
          nameError={null}
        />
      )}

      {step === 1 && (
        <StepSource
          sources={sources}
          sourceId={form.sourceId}
          onSelectSourceId={(id) => updateForm({ sourceId: id })}
          loading={sourcesQuery.isPending}
          emptyHint={sourcesQuery.isError ? "Не удалось загрузить источники (проверьте права и API)." : null}
        />
      )}

      {step === 2 && (
        <StepSourceCredentials
          configText={form.credentialsConfigText}
          needsPersist={form.credentialsSavedText !== form.credentialsConfigText}
          onChangeText={(credentialsConfigText) => updateForm({ credentialsConfigText })}
          onSaveConfig={onSaveCredentials}
          saving={patchCfgMutation.isPending}
          saveError={saveCredError}
        />
      )}

      {step === 3 && (
        <StepCheckSource
          check={form.sourceCheck}
          checking={checkSrcMutation.isPending}
          onRunCheck={onRunSourceCheck}
          checkError={checkSrcErr}
        />
      )}

      {step === 4 && (
        <StepDiscoverStreams
          discovery={form.discovery}
          discoveryError={form.discoveryError}
          discovering={discoverMutation.isPending}
          onDiscover={onDiscover}
          enabledStreamNames={form.enabledStreamNames}
          streamOptions={form.streamOptions}
          onToggleStream={onToggleStream}
          onChangeStreamOption={onChangeStreamOption}
        />
      )}

      {step === 5 && (
        <StepDestination
          destinations={destinations}
          destinationId={form.destinationId}
          onSelectDestinationId={(id) => updateForm({ destinationId: id })}
          loading={destQuery.isPending}
        />
      )}

      {step === 6 && (
        <StepCheckDestination
          check={form.destinationCheck}
          checking={checkDstMutation.isPending}
          onRunCheck={onRunDestCheck}
          checkError={checkDstErr}
        />
      )}

      {step === 7 && <StepMapping rows={form.mappingRows} onChangeRow={onChangeMappingRow} />}

      {step === 8 && (
        <StepNormalization
          enabled={form.normalizationEnabled}
          onToggle={(normalizationEnabled) => updateForm({ normalizationEnabled })}
        />
      )}

      {step === 9 && (
        <StepSchedule
          cron={form.scheduleCron}
          timezone={form.timezone}
          onChange={(p) => updateForm(p)}
        />
      )}

      {step === 10 && (
        <StepReview
          form={form}
          sourceLabel={sourceLabel}
          destinationLabel={destinationLabel}
          preflightRunning={preflightRunning}
        />
      )}

      {step === 11 && (
        <StepSaveRun
          saving={saveConnectionMutation.isPending && saveAction === "save"}
          triggering={saveConnectionMutation.isPending && saveAction === "run"}
          saveError={submitErr}
          doneMessage={doneMsg}
          onSaveOnly={onSaveOnly}
          onSaveAndRun={onSaveAndRun}
        />
      )}

      <div className="mt-4 flex justify-between">
        <Button type="button" variant="outline" onClick={goBack} disabled={step === 0 || saveConnectionMutation.isPending} data-testid="button-step-back">
          Назад
        </Button>
        {step < WIZARD_STEP_COUNT - 1 ? (
          <Button
            type="button"
            onClick={goNext}
            disabled={blocked || busyNav || (step === 10 && preflightRunning)}
            data-testid="button-step-next"
          >
            Далее
          </Button>
        ) : null}
      </div>
    </div>
  );
}
