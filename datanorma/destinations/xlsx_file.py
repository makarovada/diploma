"""Приёмник XLSX (openpyxl через pandas)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from datanorma.destinations.base import (
    BaseDestination,
    DestinationCheckResult,
    DestinationWriteResult,
    WriteMode,
)


def _path(config: dict[str, Any]) -> Path:
    base = str(config.get("path") or "").strip()
    if not base:
        raise ValueError("В config нужен path к .xlsx для XLSX destination.")
    return Path(base).resolve()


def _sheet(config: dict[str, Any], stream_name: str) -> str:
    s = str(config.get("sheet_name") or stream_name or "data").strip() or "data"
    return s[:31]


class XlsxFileDestination(BaseDestination):
    code = "xlsx"

    def check(self, config: dict[str, Any]) -> DestinationCheckResult:
        try:
            p = _path(config)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists() and not p.is_file():
                return DestinationCheckResult(ok=False, message=f"Путь не файл: {p}", details={})
            test = p.parent / ".datanorma_xlsx_touch"
            test.write_bytes(b"")
            test.unlink(missing_ok=True)
            return DestinationCheckResult(
                ok=True,
                message=f"XLSX: путь доступен ({p.parent}).",
                details={"path": str(p)},
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
        path = _path(config)
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet = _sheet(config, stream_name)
        rows = [dict(r) for r in records]
        pk = config.get("primary_key")
        pk_list: list[str] = []
        if isinstance(pk, str) and pk.strip():
            pk_list = [pk.strip()]
        elif isinstance(pk, list):
            pk_list = [str(x).strip() for x in pk if str(x).strip()]

        try:
            if mode in (WriteMode.full_refresh, WriteMode.replace_table):
                df = pd.DataFrame(rows)
                with pd.ExcelWriter(path, engine="openpyxl", mode="w") as writer:
                    df.to_excel(writer, sheet_name=sheet, index=False)
                return DestinationWriteResult(
                    ok=True,
                    message=f"XLSX: записано {len(rows)} строк (новая книга / лист).",
                    rows_written=len(rows),
                    details={"path": str(path), "sheet": sheet},
                )

            if mode == WriteMode.append:
                if path.exists():
                    try:
                        old = pd.read_excel(path, sheet_name=sheet)
                    except ValueError:
                        old = pd.DataFrame()
                else:
                    old = pd.DataFrame()
                df_new = pd.DataFrame(rows)
                df = pd.concat([old, df_new], ignore_index=True)
                mode_w: str = "a" if path.exists() else "w"
                if mode_w == "a":
                    with pd.ExcelWriter(
                        path,
                        engine="openpyxl",
                        mode="a",
                        if_sheet_exists="replace",
                    ) as writer:
                        df.to_excel(writer, sheet_name=sheet, index=False)
                else:
                    with pd.ExcelWriter(path, engine="openpyxl", mode="w") as writer:
                        df.to_excel(writer, sheet_name=sheet, index=False)
                return DestinationWriteResult(
                    ok=True,
                    message=f"XLSX append: +{len(rows)} строк.",
                    rows_written=len(rows),
                    details={"path": str(path), "sheet": sheet},
                )

            if mode == WriteMode.upsert:
                if not pk_list:
                    return DestinationWriteResult(
                        ok=False,
                        message="XLSX upsert: укажите primary_key.",
                        rows_written=0,
                    )
                pk0 = pk_list[0]
                old = pd.DataFrame()
                if path.exists():
                    try:
                        old = pd.read_excel(path, sheet_name=sheet)
                    except ValueError:
                        old = pd.DataFrame()
                df_new = pd.DataFrame(rows)
                df = pd.concat([old, df_new], ignore_index=True)
                df.drop_duplicates(subset=[pk0], keep="last", inplace=True)
                with pd.ExcelWriter(path, engine="openpyxl", mode="w") as writer:
                    df.to_excel(writer, sheet_name=sheet, index=False)
                return DestinationWriteResult(
                    ok=True,
                    message=f"XLSX upsert: {len(rows)} строк.",
                    rows_written=len(rows),
                    details={"path": str(path), "sheet": sheet},
                )
        except Exception as exc:
            return DestinationWriteResult(ok=False, message=str(exc), rows_written=0)
        return DestinationWriteResult(ok=False, message="Неизвестный режим.", rows_written=0)
