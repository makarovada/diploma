import type { ColumnRuleType } from "@/components/connection-wizard/column-rule-types";
import type { SchemaLayout, StreamDefaultDto, WizardColumnRuleRow } from "@/components/connection-wizard/wizard-types";
import type {
  EltConnectionColumnRuleDto,
  EltConnectionDetailDto,
  EltConnectionPatchPayload,
  EltConnectionStreamRowDto,
  IngestCatalogDto,
  EltDiscoverResponseDto,
} from "@/lib/api-types";
import {
  encodeCursorFields,
  encodePrimaryKeyFields,
  parseCursorFields,
  parsePrimaryKeyFields,
} from "@/lib/destination-sync-mode";

export function detailStreamsToDefaults(streams: EltConnectionStreamRowDto[]): StreamDefaultDto[] {
  return streams.map((s) => ({
    stream_name: s.stream_name,
    sync_mode: s.sync_mode || "full_refresh",
    destination_sync_mode: s.destination_sync_mode || "refresh_overwrite",
    cursor_field: parseCursorFields(s.cursor_field),
    primary_key: parsePrimaryKeyFields(s.primary_key),
  }));
}

export function mergeStreamDefaultsWithDiscover(
  fromDetail: StreamDefaultDto[],
  discoverDefaults: StreamDefaultDto[],
): StreamDefaultDto[] {
  const byName = new Map(fromDetail.map((d) => [d.stream_name, d]));
  for (const d of discoverDefaults) {
    const cur = byName.get(d.stream_name);
    if (!cur) {
      byName.set(d.stream_name, {
        ...d,
        cursor_field: parseCursorFields(d.cursor_field as string | string[] | null),
        primary_key: parsePrimaryKeyFields(d.primary_key as string | string[] | null),
      });
      continue;
    }
    byName.set(d.stream_name, {
      ...cur,
      sync_mode: cur.sync_mode || d.sync_mode,
      destination_sync_mode: cur.destination_sync_mode || d.destination_sync_mode,
    });
  }
  return Array.from(byName.values());
}

export function columnRulesDtoToWizardRows(
  rules: EltConnectionColumnRuleDto[],
  layout: SchemaLayout,
): WizardColumnRuleRow[] {
  return rules.map((r, idx) => {
    const entity = r.entity ?? (layout === "flat" ? null : r.entity);
    const streamKey = entity ?? "flat";
    return {
      id: `${streamKey}:${r.source_field}:${idx}`,
      entity,
      sourceField: r.source_field,
      targetField: r.target_field || r.source_field,
      ruleType: r.type as ColumnRuleType,
      required: Boolean(r.required),
    };
  });
}

export function layoutFromDetail(detail: EltConnectionDetailDto): SchemaLayout {
  const wm = detail.wizard_meta;
  if (wm && typeof wm === "object" && wm.layout === "entities") return "entities";
  const streams = detail.streams ?? [];
  if (streams.length > 1) return "entities";
  return "flat";
}

export function enabledStreamNames(detail: EltConnectionDetailDto): string[] {
  return (detail.streams ?? []).filter((s) => s.is_enabled).map((s) => s.stream_name);
}

export function discoverResponseToState(resp: EltDiscoverResponseDto): {
  layout: SchemaLayout;
  entityLabels: Record<string, string>;
  discovery: IngestCatalogDto;
  streamDefaults: StreamDefaultDto[];
} {
  const layout = (resp.layout ?? "flat") as SchemaLayout;
  const streamDefaults: StreamDefaultDto[] = (resp.stream_defaults ?? []).map((d) => ({
    stream_name: d.stream_name,
    sync_mode: d.sync_mode || "full_refresh",
    destination_sync_mode: d.destination_sync_mode ?? "refresh_overwrite",
    cursor_field: parseCursorFields(d.cursor_field as string | string[] | null),
    primary_key: parsePrimaryKeyFields(d.primary_key as string | string[] | null),
  }));
  return {
    layout,
    entityLabels: resp.entity_labels ?? {},
    discovery: resp.catalog,
    streamDefaults,
  };
}

export function buildConnectionStreamsPatchPayload(args: {
  detail: EltConnectionDetailDto;
  streamDefaults: StreamDefaultDto[];
  columnRuleRows: WizardColumnRuleRow[];
  layout: SchemaLayout;
}): EltConnectionPatchPayload {
  const { detail, streamDefaults, columnRuleRows, layout } = args;
  const defaultsByName = new Map(streamDefaults.map((d) => [d.stream_name, d]));
  const streams = (detail.streams ?? []).map((s) => {
    const d = defaultsByName.get(s.stream_name);
    const sync_mode = (d?.sync_mode ?? s.sync_mode ?? "full_refresh") as "full_refresh" | "incremental";
    return {
      stream_name: s.stream_name,
      sync_mode,
      destination_sync_mode: d?.destination_sync_mode ?? s.destination_sync_mode ?? "refresh_overwrite",
      cursor_field: encodeCursorFields(d?.cursor_field ?? parseCursorFields(s.cursor_field)),
      primary_key: encodePrimaryKeyFields(d?.primary_key ?? parsePrimaryKeyFields(s.primary_key)),
      is_enabled: s.is_enabled,
    };
  });
  const column_rules = columnRuleRows.map((r) => ({
    entity: layout === "entities" ? r.entity : r.entity ?? streams[0]?.stream_name ?? null,
    source_field: r.sourceField,
    target_field: r.targetField.trim() || r.sourceField,
    type: r.ruleType,
    required: r.required,
  }));
  const wm = detail.wizard_meta && typeof detail.wizard_meta === "object" ? { ...detail.wizard_meta } : {};
  const wizard_meta = {
    ...wm,
    v: 2,
    layout,
    column_rules,
    selected_entities: enabledStreamNames(detail),
  };
  return { streams, column_rules, wizard_meta };
}
