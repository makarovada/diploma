"""Сырой слой: выгрузка 1С (CSV/Excel из файла по умолчанию — sample)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import logging

import dagster as dg
import pandas as pd

from datanorma.resources.paths import DataPathsResource

_log = logging.getLogger(__name__)


def _read_1c_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(path, engine="openpyxl")
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path, encoding="utf-8")
    raise ValueError(f"Неподдерживаемый формат 1С-выгрузки: {path}")


@dg.asset(
    group_name="raw",
    description="Документы продаж 1С: DATANORMA_1C_EXPORT_PATH или data/samples/1c_export.csv",
    compute_kind="file",
)
def raw_1c_orders(paths: DataPathsResource) -> dict:
    override = os.environ.get("DATANORMA_1C_EXPORT_PATH", "").strip()
    if override:
        export_path = Path(override)
        ingest_mode = "1c_file_env"
    else:
        export_path = paths.sample_file("1c_export.csv")
        ingest_mode = "1c_sample_csv"

    if not export_path.is_file():
        raise FileNotFoundError(
            f"Файл выгрузки 1С не найден: {export_path}. "
            "Укажите DATANORMA_1C_EXPORT_PATH или положите sample в data/samples."
        )

    df = _read_1c_table(export_path)
    records = df.fillna("").to_dict(orient="records")
    _log.info("1С: строк %s из %s", len(records), export_path)

    return {
        "source_system": "1c",
        "ingest_mode": ingest_mode,
        "source_path": str(export_path.resolve()),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "columns": list(df.columns),
        "rows": records,
    }
