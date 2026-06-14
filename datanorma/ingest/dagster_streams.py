"""Потоки warehouse-контура Dagster: единый список integration_code + stream_name."""

from __future__ import annotations

from dataclasses import dataclass

from datanorma.ingest.stream_config import staging_table_physical_name


@dataclass(frozen=True)
class DagsterWarehouseStream:
    integration_code: str
    stream_name: str
    compute_kind: str
    description: str

    @property
    def raw_asset_name(self) -> str:
        safe_stream = self.stream_name.replace("-", "_")
        return f"raw_{self.integration_code}_{safe_stream}"

    @property
    def staging_table(self) -> str:
        return staging_table_physical_name(self.integration_code, self.stream_name)


def dagster_staging_table_names() -> list[str]:
    return [stream.staging_table for stream in DAGSTER_WAREHOUSE_STREAMS]


DAGSTER_WAREHOUSE_STREAMS: tuple[DagsterWarehouseStream, ...] = (
    DagsterWarehouseStream(
        integration_code="google_sheet",
        stream_name="orders",
        compute_kind="google_sheets",
        description="Google Sheets: GSPREAD_* или data/samples/google_sheet_export.csv.",
    ),
    DagsterWarehouseStream(
        integration_code="bitrix24",
        stream_name="crm_deals",
        compute_kind="bitrix24",
        description="Bitrix24 CRM: webhook или фикстуры data/fixtures/bitrix24/.",
    ),
)
