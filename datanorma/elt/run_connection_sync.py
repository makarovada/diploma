"""Прогон доменного connection: для каждого включённого потока source.read → destination_write → sync_state."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from datanorma.destinations.registry import destination_write, normalize_destination_kind
from datanorma.elt.sync_mode_policy import (
    effective_source_sync_mode,
    parse_cursor_field,
    parse_primary_key_field,
    resolve_write_mode,
)
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.warehouse.sync_state_repo import build_ingest_state_dict, extract_stream_cursor
from datanorma.normalization.typing import cast_row
from datanorma.web.elt_repo import (
    get_connection,
    get_destination,
    get_source,
    load_stream_rules_for_sync,
    public_destination_payload,
    public_source_payload,
)

_log = logging.getLogger(__name__)


def _pick_field_value(row: dict[str, Any], cursor_field: str | None) -> str | None:
    if not cursor_field:
        return None
    cf = cursor_field.strip()
    cf_norm = cf.lower().replace("_", "")
    for k, v in row.items():
        if str(k).lower().replace("_", "") == cf_norm:
            return str(v) if v is not None else None
        if str(k) == cf:
            return str(v) if v is not None else None
    return None


def _max_cursor(records: list[dict[str, Any]], cursor_field: str | None) -> str | None:
    if not cursor_field or not records:
        return None
    vals = []
    for r in records:
        v = _pick_field_value(r, cursor_field)
        if v and str(v).strip():
            vals.append(str(v).strip())
    if not vals:
        return None
    return max(vals)


def _write_normalization_issues(
    conn: Connection,
    *,
    sync_run_id: int,
    connection_id: int,
    stream_name: str,
    issues: list[dict[str, Any]],
) -> None:
    for iss in issues:
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO normalization_issue
                      (sync_run_id, connection_id, stream_name, target_field, error_code, error_text, raw_value)
                    VALUES
                      (:run_id, :cid, :sn, :tf, :ec, :et, CAST(:rv AS jsonb))
                    """
                ),
                {
                    "run_id": sync_run_id,
                    "cid": connection_id,
                    "sn": stream_name,
                    "tf": iss.get("field"),
                    "ec": iss.get("error_code") or "cast_error",
                    "et": iss.get("error_text"),
                    "rv": json.dumps(iss.get("raw_value"), ensure_ascii=False) if iss.get("raw_value") is not None else None,
                },
            )
        except Exception:
            continue


def run_connection_sync(
    conn: Connection,
    *,
    workspace_id: int,
    domain_connection_id: int,
    sync_run_id: int | None = None,
) -> dict[str, Any]:
    """Выполняет синхронизацию всех включённых потоков connection. Возвращает summary dict."""
    crow = get_connection(conn, workspace_id=workspace_id, connection_id=domain_connection_id)
    if crow is None:
        raise ValueError("connection not found")

    src_row = get_source(conn, workspace_id=workspace_id, source_id=int(crow["source_id"]))
    dst_row = get_destination(conn, workspace_id=workspace_id, destination_id=int(crow["destination_id"]))
    if src_row is None or dst_row is None:
        raise ValueError("source or destination not found")

    sp = public_source_payload(src_row)
    dp = public_destination_payload(dst_row)
    cfg_src = sp.get("config") or {}
    cfg_dst = dp.get("config") or {}
    cc_src = str(sp.get("connector_code") or "").strip().lower().replace("-", "_")
    cc_dst = normalize_destination_kind(str(dp.get("connector_code") or ""))

    yaml_text = cfg_src.get("yaml_body") or cfg_src.get("connector_builder_yaml")
    paths = DataPathsResource()
    src = create_source(
        cc_src,
        paths=paths,
        yaml_text=str(yaml_text) if yaml_text and str(yaml_text).strip() else None,
        source_config=cfg_src if isinstance(cfg_src, dict) else {},
    )

    streams = [s for s in (crow.get("streams") or []) if s.get("is_enabled")]
    if not streams:
        raise ValueError("Нет включённых потоков в connection.")

    per_stream: list[dict[str, Any]] = []
    total_rows = 0
    total_issues = 0

    for cs in streams:
        csid = int(cs["id"])
        sn = str(cs["stream_name"]).strip()
        sync_mode = str(cs.get("sync_mode") or "full_refresh").strip()
        destination_sync_mode = cs.get("destination_sync_mode")
        destination_sync_mode = (
            str(destination_sync_mode).strip() if destination_sync_mode else None
        )
        eff_sync_mode = effective_source_sync_mode(
            sync_mode=sync_mode, destination_sync_mode=destination_sync_mode
        )
        cursor_fields = parse_cursor_field(cs.get("cursor_field"))
        cursor_field = cursor_fields[0] if cursor_fields else None
        pk_cols = parse_primary_key_field(cs.get("primary_key"))

        ss_row = conn.execute(
            text(
                "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state "
                "FROM sync_state WHERE connection_stream_id = :csid AND workspace_id = :wid"
            ),
            {"csid": csid, "wid": workspace_id},
        ).mappings().first()
        if ss_row is None:
            ss_row = conn.execute(
                text(
                    "SELECT id, integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state "
                    "FROM sync_state WHERE connection_stream_id = :csid"
                ),
                {"csid": csid},
            ).mappings().first()
        if ss_row is None:
            raise RuntimeError(f"sync_state не найден для connection_stream id={csid}")

        last_cursor = extract_stream_cursor(dict(ss_row))

        records = list(
            src.read(
                sn,
                sync_mode=eff_sync_mode,
                cursor_field=cursor_field,
                last_cursor=last_cursor,
            )
        )

        stream_rules = load_stream_rules_for_sync(
            conn, connection_id=domain_connection_id, stream_name=sn
        )
        norm_issues: list[dict[str, Any]] = []
        if stream_rules and stream_rules.columns:
            normalized_records: list[dict[str, Any]] = []
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                row, issues = cast_row(stream_rules, rec)
                normalized_records.append(row)
                norm_issues.extend(issues)
            records = normalized_records
            if sync_run_id is not None and norm_issues:
                _write_normalization_issues(
                    conn,
                    sync_run_id=sync_run_id,
                    connection_id=domain_connection_id,
                    stream_name=sn,
                    issues=norm_issues,
                )
            total_issues += len(norm_issues)

        schema = records_to_json_schema(records[:120] if records else [])
        wm = resolve_write_mode(sync_mode=sync_mode, destination_sync_mode=destination_sync_mode)
        write_cfg = dict(cfg_dst)
        if pk_cols:
            write_cfg["primary_key"] = pk_cols if len(pk_cols) > 1 else pk_cols[0]

        wr = destination_write(
            cc_dst,
            stream_name=sn,
            records=records,
            schema=schema,
            mode=wm,
            config=write_cfg,
        )
        if not wr.ok:
            raise RuntimeError(f"Приёмник {cc_dst}, поток {sn}: {wr.message}")

        rows_written = int(wr.rows_written or len(records))
        total_rows += rows_written

        new_cursor: str | None = None
        if eff_sync_mode == "incremental" and cursor_field:
            new_cursor = _max_cursor(records, cursor_field)

        ingest = build_ingest_state_dict(
            cursor=new_cursor,
            rows_emitted=rows_written,
            batch_id=f"elt-{domain_connection_id}-{uuid.uuid4().hex[:12]}",
        )
        cv_text = json.dumps({"cursor": new_cursor}, ensure_ascii=False) if new_cursor else json.dumps({}, ensure_ascii=False)

        conn.execute(
            text(
                "UPDATE sync_state SET cursor_value = CAST(:cv AS text), ingest_state = CAST(:ing AS jsonb), "
                "last_success_at = NOW(), updated_at = NOW() WHERE id = :sid"
            ),
            {"cv": cv_text, "ing": json.dumps(ingest, ensure_ascii=False), "sid": int(ss_row["id"])},
        )

        per_stream.append(
            {
                "stream_name": sn,
                "rows_written": rows_written,
                "cursor_updated_to": new_cursor,
                "sync_mode": eff_sync_mode,
                "destination_sync_mode": destination_sync_mode,
                "write_mode": wm.value,
            }
        )

    return {
        "streams": per_stream,
        "total_rows_written": total_rows,
        "total_issues": total_issues,
        "source_connector": cc_src,
        "destination_connector": cc_dst,
    }
