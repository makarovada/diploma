#!/usr/bin/env python3
"""API E2E: google_sheet source → postgres destination → connection → trigger.

Запуск из контейнера fastapi (sink на host.docker.internal:5544):
  docker compose exec fastapi python /app/scripts/e2e_google_sheet_elt_api.py

Или с хоста (API :8080, sink :5544):
  python scripts/e2e_google_sheet_elt_api.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

import httpx

BASE = os.environ.get("E2E_API_BASE", "http://127.0.0.1:8080").rstrip("/")
WORKSPACE = os.environ.get("E2E_WORKSPACE", "main")
USER = os.environ.get("E2E_USER", "seed_admin")
PASSWORD = os.environ.get("E2E_PASSWORD", "AdminDemo2026")

SINK_CONFIG = {
    "url": os.environ.get(
        "TEST_SINK_URL",
        "postgresql://test_user:test_pass@host.docker.internal:5544/test_sink",
    ),
    "schema": "public",
    "table": "elt_test_load",
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    with httpx.Client(base_url=BASE, timeout=120.0, trust_env=False) as client:
        login = client.post("/api/auth/login", json={"username": USER, "password": PASSWORD})
        if login.status_code != 200:
            print("LOGIN FAILED", login.status_code, login.text, file=sys.stderr)
            return 1
        token = login.json().get("access_token") or login.json().get("token")
        if not token:
            print("LOGIN: no token in response", login.json(), file=sys.stderr)
            return 1
        h = _headers(token)

        src_body = {
            "workspace_code": WORKSPACE,
            "name": f"E2E Sheets {suffix}",
            "connector_code": "google_sheet",
            "config": {
                "spreadsheet_id": os.environ.get("E2E_SPREADSHEET_ID", "e2e-placeholder"),
                "worksheet": "0",
                "service_account_json": json.loads(
                    os.environ.get("E2E_SERVICE_ACCOUNT_JSON", '{"type":"service_account","project_id":"e2e"}')
                ),
            },
        }
        r = client.post("/api/v1/sources", headers=h, json=src_body)
        if r.status_code not in (200, 201):
            print("CREATE SOURCE FAILED", r.status_code, r.text, file=sys.stderr)
            return 1
        source_id = int(r.json()["item"]["id"])
        print(f"source_id={source_id}")

        chk = client.post(f"/api/v1/sources/{source_id}/check", headers=h, params={"workspace_code": WORKSPACE})
        chk_body = chk.json()
        print("source check:", chk_body.get("ok"), chk_body.get("message"), chk_body.get("details"))
        if not chk_body.get("ok"):
            print("SOURCE CHECK FAILED", file=sys.stderr)
            return 1

        disc = client.post(f"/api/v1/sources/{source_id}/discover", headers=h, params={"workspace_code": WORKSPACE})
        if disc.status_code != 200:
            print("DISCOVER FAILED", disc.status_code, disc.text, file=sys.stderr)
            return 1
        streams = disc.json().get("catalog", {}).get("streams") or disc.json().get("streams") or []
        stream_names = [s["name"] for s in streams]
        print("streams:", stream_names)
        if "orders" not in stream_names:
            print("EXPECTED stream 'orders'", file=sys.stderr)
            return 1

        dst_body = {
            "workspace_code": WORKSPACE,
            "name": f"E2E PG Sink {suffix}",
            "connector_code": "postgres",
            "config": SINK_CONFIG,
        }
        r = client.post("/api/v1/destinations", headers=h, json=dst_body)
        if r.status_code not in (200, 201):
            print("CREATE DESTINATION FAILED", r.status_code, r.text, file=sys.stderr)
            return 1
        dest_id = int(r.json()["item"]["id"])
        print(f"destination_id={dest_id}")

        dchk = client.post(
            f"/api/v1/destinations/{dest_id}/check",
            headers=h,
            params={"workspace_code": WORKSPACE},
        )
        dchk_body = dchk.json()
        print("destination check:", dchk_body.get("ok"), dchk_body.get("message"))
        if not dchk_body.get("ok"):
            print("DESTINATION CHECK FAILED", file=sys.stderr)
            return 1

        conn_body = {
            "workspace_code": WORKSPACE,
            "name": f"E2E Connection {suffix}",
            "description": "API E2E google_sheet → postgres",
            "source_id": source_id,
            "destination_id": dest_id,
            "schedule_cron": None,
            "timezone": "UTC",
            "streams": [
                {
                    "stream_name": "orders",
                    "sync_mode": "full_refresh",
                    "cursor_field": None,
                    "is_enabled": True,
                }
            ],
        }
        r = client.post("/api/v1/connections", headers=h, json=conn_body)
        if r.status_code not in (200, 201):
            print("CREATE CONNECTION FAILED", r.status_code, r.text, file=sys.stderr)
            return 1
        conn_id = int(r.json()["item"]["id"])
        print(f"connection_id={conn_id}")

        tr = client.post(
            f"/api/v1/connections/{conn_id}/trigger",
            headers=h,
            params={"workspace_code": WORKSPACE},
        )
        if tr.status_code != 202:
            print("TRIGGER FAILED", tr.status_code, tr.text, file=sys.stderr)
            return 1
        summary = tr.json().get("summary") or {}
        total = summary.get("total_rows_written", 0)
        print("trigger summary:", json.dumps(summary, ensure_ascii=False))
        if int(total or 0) < 1:
            print("EXPECTED total_rows_written >= 1", file=sys.stderr)
            return 1

        print("E2E OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
