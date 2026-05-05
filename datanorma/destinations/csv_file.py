"""Приёмник CSV: запись в локальный файл."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from datanorma.destinations.base import (
    BaseDestination,
    DestinationCheckResult,
    DestinationWriteResult,
    WriteMode,
)


def _path(config: dict[str, Any], stream_name: str) -> Path:
    base = str(config.get("path") or config.get("directory") or "").strip()
    if not base:
        raise ValueError("В config нужен path (файл или каталог) для CSV destination.")
    p = Path(base)
    if p.is_dir() or str(base).endswith(("/", "\\")):
        safe_stream = "".join(c if c.isalnum() or c in "-_" else "_" for c in stream_name)
        fname = str(config.get("filename") or f"{safe_stream}.csv").strip()
        return (p / fname).resolve()
    return p.resolve()


def _rows(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(r) for r in records]


class CsvFileDestination(BaseDestination):
    code = "csv"

    def check(self, config: dict[str, Any]) -> DestinationCheckResult:
        try:
            p = _path(config, str(config.get("_check_stream") or "default"))
            parent = p.parent
            parent.mkdir(parents=True, exist_ok=True)
            if p.exists() and not p.is_file():
                return DestinationCheckResult(ok=False, message=f"Путь занят не файлом: {p}", details={})
            test = parent / ".datanorma_write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return DestinationCheckResult(
                ok=True,
                message=f"CSV: каталог доступен ({parent}).",
                details={"resolved_path": str(p)},
            )
        except Exception as exc:
            return DestinationCheckResult(ok=False, message=str(exc), details={})

    def write(
        self,
        stream_name: str,
        records: Iterable[dict[str, Any]],
        schema: dict[str, Any],
        mode: WriteMode,
        config: dict[str, Any],
    ) -> DestinationWriteResult:
        rows = _rows(records)
        path = _path(config, stream_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoding = str(config.get("encoding") or "utf-8")
        delimiter = str(config.get("delimiter") or ",")
        pk = config.get("primary_key")
        pk_list: list[str] = []
        if isinstance(pk, str) and pk.strip():
            pk_list = [pk.strip()]
        elif isinstance(pk, list):
            pk_list = [str(x).strip() for x in pk if str(x).strip()]

        try:
            if mode in (WriteMode.full_refresh, WriteMode.replace_table) or (
                mode == WriteMode.append and not path.exists()
            ):
                if not rows:
                    path.write_text("", encoding=encoding)
                    return DestinationWriteResult(
                        ok=True,
                        message="CSV: пустой файл создан.",
                        rows_written=0,
                        details={"path": str(path)},
                    )
                fieldnames = sorted({k for r in rows for k in r})
                with path.open("w", encoding=encoding, newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                    w.writeheader()
                    w.writerows(rows)
                return DestinationWriteResult(
                    ok=True,
                    message=f"CSV: записано {len(rows)} строк (новый файл).",
                    rows_written=len(rows),
                    details={"path": str(path), "mode": mode.value},
                )

            if mode == WriteMode.append:
                if not rows:
                    return DestinationWriteResult(ok=True, message="Нет строк.", rows_written=0)
                existing: list[dict[str, Any]] = []
                fieldnames: list[str] = []
                if path.exists():
                    with path.open(encoding=encoding, newline="") as f:
                        r = csv.DictReader(f, delimiter=delimiter)
                        fieldnames = list(r.fieldnames or [])
                        existing = [dict(row) for row in r]
                fieldnames = sorted(set(fieldnames) | {k for r in rows for k in r})
                merged = existing + rows
                with path.open("w", encoding=encoding, newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                    w.writeheader()
                    w.writerows(merged)
                return DestinationWriteResult(
                    ok=True,
                    message=f"CSV: append, всего строк {len(merged)}.",
                    rows_written=len(rows),
                    details={"path": str(path)},
                )

            # upsert: по primary_key
            if not pk_list:
                return DestinationWriteResult(
                    ok=False,
                    message="CSV upsert: укажите primary_key в config.",
                    rows_written=0,
                )
            pk0 = pk_list[0]
            existing: list[dict[str, Any]] = []
            fieldnames: list[str] = []
            if path.exists():
                with path.open(encoding=encoding, newline="") as f:
                    r = csv.DictReader(f, delimiter=delimiter)
                    fieldnames = list(r.fieldnames or [])
                    existing = [dict(row) for row in r]
            by_key = {str(row.get(pk0)): row for row in existing if pk0 in row}
            for row in rows:
                by_key[str(row.get(pk0))] = row
            merged = list(by_key.values())
            fieldnames = sorted(set(fieldnames) | {k for r in merged for k in r})
            with path.open("w", encoding=encoding, newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                w.writeheader()
                w.writerows(merged)
            return DestinationWriteResult(
                ok=True,
                message=f"CSV upsert: {len(rows)} входных, {len(merged)} в файле.",
                rows_written=len(rows),
                details={"path": str(path)},
            )
        except Exception as exc:
            return DestinationWriteResult(ok=False, message=str(exc), rows_written=0)
