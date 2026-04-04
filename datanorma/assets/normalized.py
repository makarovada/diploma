import dagster as dg

from datanorma.normalization.to_canonical import build_canonical_sales_rows, load_source_mappings


@dg.asset(
    group_name="normalized",
    description="Каноника: YAML-маппинг, fuzzy колонок, даты→MSK, amount_rub по ЦБ РФ, дедуп. "
    "Зависит от staging_raw_postgres, чтобы raw сначала попал в PostgreSQL (фаза B).",
)
def normalized_orders(
    raw_ozon_postings: dict,
    raw_1c_orders: dict,
    raw_google_sheet_orders: dict,
    staging_raw_postgres: dict,
) -> dict:
    _ = staging_raw_postgres
    mappings = load_source_mappings()
    rows, stats = build_canonical_sales_rows(
        raw_ozon_postings,
        raw_1c_orders,
        raw_google_sheet_orders,
        mappings=mappings,
    )
    return {
        "canonical_schema": mappings.get("canonical"),
        "mappings_version": mappings.get("version"),
        "rows": rows,
        "stats": stats,
        "raw_row_counts": {
            "ozon": raw_ozon_postings["row_count"],
            "1c": raw_1c_orders["row_count"],
            "google_sheet": raw_google_sheet_orders["row_count"],
        },
    }
