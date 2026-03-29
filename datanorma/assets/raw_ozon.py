"""Сырой слой: Ozon Seller API (при наличии ключей) или локальная выборка JSON."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import logging

import dagster as dg
import httpx

from datanorma.resources.paths import DataPathsResource

_log = logging.getLogger(__name__)

OZON_API_BASE = "https://api-seller.ozon.ru"


def _load_fixture(paths: DataPathsResource) -> list[dict]:
    path = paths.sample_file("ozon_postings.json")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    postings = data.get("result", {}).get("postings")
    if postings is None:
        postings = data.get("postings", [])
    return list(postings)


def _fetch_postings_api(client_id: str, api_key: str, limit: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = {
        "dir": "DESC",
        "filter": {"since": since, "to": to},
        "limit": min(max(limit, 1), 1000),
        "offset": 0,
        "with": {
            "analytics_data": True,
            "financial_data": True,
            "barcodes": False,
        },
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{OZON_API_BASE}/v3/posting/fbs/list",
            headers={
                "Client-Id": client_id,
                "Api-Key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
    return list(body.get("result", {}).get("postings", []))


@dg.asset(
    group_name="raw",
    description="Отправления Ozon (FBS list). Без OZON_CLIENT_ID/OZON_API_KEY — из data/samples.",
    compute_kind="ozon_api",
)
def raw_ozon_postings(paths: DataPathsResource) -> dict:
    client_id = os.environ.get("OZON_CLIENT_ID", "").strip()
    api_key = os.environ.get("OZON_API_KEY", "").strip()
    limit = int(os.environ.get("OZON_FETCH_LIMIT", "100"))

    if client_id and api_key:
        try:
            postings = _fetch_postings_api(client_id, api_key, limit=limit)
            ingest_mode = "ozon_api"
            _log.info("Ozon API: получено отправлений %s", len(postings))
        except Exception as exc:
            _log.warning("Ozon API недоступен (%s), читаем фикстуру", exc)
            postings = _load_fixture(paths)
            ingest_mode = "fixture_fallback"
    else:
        _log.info("Ключи Ozon не заданы, читаем фикстуру")
        postings = _load_fixture(paths)
        ingest_mode = "fixture"

    return {
        "source_system": "ozon",
        "ingest_mode": ingest_mode,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(postings),
        "postings": postings,
    }
