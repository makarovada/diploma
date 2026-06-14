from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.schedules import connection_cron_runner as mod

pytestmark = pytest.mark.unit


def test_run_scheduled_sync_runs_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(mod, "create_sync_run", lambda *_a, **_k: {"id": 55})
    called: dict[str, bool] = {"inline": False}
    monkeypatch.setattr(
        mod,
        "run_sync_inline_for_connection",
        lambda *_a, **_k: called.__setitem__("inline", True) or ({"id": 55, "status": "success"}, {"total_rows_written": 1}),
    )

    mod.run_scheduled_sync(
        conn,
        workspace_id=1,
        domain_connection_id=7,
        integration_code="google_sheet",
        slot_key="2026-06-02T12:00:00+00:00|UTC",
    )

    assert called["inline"] is True


def test_run_scheduled_sync_marks_failed_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(mod, "create_sync_run", lambda *_a, **_k: {"id": 56})
    monkeypatch.setattr(
        mod,
        "run_sync_inline_for_connection",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    failed: dict[str, bool] = {"called": False}
    monkeypatch.setattr(mod, "mark_sync_run_failed", lambda *_a, **_k: failed.__setitem__("called", True))

    with pytest.raises(RuntimeError, match="boom"):
        mod.run_scheduled_sync(
            conn,
            workspace_id=1,
            domain_connection_id=7,
            integration_code="google_sheet",
            slot_key="2026-06-02T12:01:00+00:00|UTC",
        )

    assert failed["called"] is True

