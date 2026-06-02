from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.schedules import connection_cron_runner as mod

pytestmark = pytest.mark.unit


def test_run_scheduled_sync_launches_dagster(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(mod, "create_sync_run", lambda *_a, **_k: {"id": 55})
    called: dict[str, bool] = {"running": False}
    monkeypatch.setattr(mod, "launch_sync_run_via_dagster", lambda *_a, **_k: called.__setitem__("running", True))

    mod.run_scheduled_sync(
        conn,
        workspace_id=1,
        domain_connection_id=7,
        integration_code="ozon",
        slot_key="2026-06-02T12:00:00+00:00|UTC",
    )

    assert called["running"] is True


def test_run_scheduled_sync_fallbacks_to_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(mod, "create_sync_run", lambda *_a, **_k: {"id": 56})
    monkeypatch.setattr(mod, "launch_sync_run_via_dagster", lambda *_a, **_k: (_ for _ in ()).throw(mod.SyncRunError("down")))
    called: dict[str, bool] = {"inline_started": False, "success": False}
    def _fallback(*_a, **_k):
        called["inline_started"] = True
        called["success"] = True
        return {"id": 56, "status": "success"}, {"total_rows_written": 1, "streams": []}
    monkeypatch.setattr(mod, "run_sync_inline_fallback", _fallback)

    mod.run_scheduled_sync(
        conn,
        workspace_id=1,
        domain_connection_id=7,
        integration_code="ozon",
        slot_key="2026-06-02T12:01:00+00:00|UTC",
    )

    assert called["inline_started"] is True
    assert called["success"] is True

