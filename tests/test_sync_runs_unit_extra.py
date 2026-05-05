from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from datanorma.web import sync_runs as sr

pytestmark = pytest.mark.unit


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def one(self):
        return self.rows[0]


def test_discover_job_selector_and_launch_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def _graphql(query: str, variables: dict):
        if "ReposAndJobs" in query:
            return {
                "repositoriesOrError": {
                    "__typename": "RepositoryConnection",
                    "nodes": [{"name": "repo", "location": {"name": "loc"}, "jobs": [{"name": "daily_refresh"}], "pipelines": []}],
                }
            }
        return {"launchPipelineExecution": {"__typename": "LaunchPipelineRunSuccess", "run": {"runId": "dag-1", "status": "STARTED"}}}

    monkeypatch.setattr(sr, "_run_graphql", _graphql)
    out = sr.launch_dagster_run(sync_run_id=1, integration_code="ozon", stream_name="orders", triggered_by="seed")
    assert out.run_id == "dag-1"
    assert out.status == "running"


def test_launch_dagster_run_error_and_status_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sr,
        "_discover_job_selector",
        lambda **_k: {"repositoryLocationName": "loc", "repositoryName": "repo", "pipelineName": "daily_refresh"},
    )
    monkeypatch.setattr(
        sr,
        "_run_graphql",
        lambda *_a, **_k: {"launchPipelineExecution": {"__typename": "RunConfigValidationInvalid", "errors": [{"message": "bad config"}]}},
    )
    with pytest.raises(sr.SyncRunError, match="config invalid"):
        sr.launch_dagster_run(sync_run_id=1, integration_code=None, stream_name=None, triggered_by="u")

    monkeypatch.setattr(
        sr,
        "_run_graphql",
        lambda *_a, **_k: {"pipelineRunOrError": {"__typename": "PipelineRun", "status": "SUCCESS", "endTime": 1715000000}},
    )
    st, finished = sr.fetch_dagster_run_status("run-1")
    assert st == "success"
    assert isinstance(finished, datetime)


def test_resolve_connection_variants_and_attach_destination() -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _Rows([{"sync_id": 10, "ic": "ozon", "sn": "orders", "dcid": 5}]),
        _Rows([{"id": 11, "integration_code": "1c", "stream_name": "sales", "domain_cid": 6}]),
        _Rows([{"id": 12, "integration_code": "sheet", "stream_name": "rows", "domain_cid": None}]),
        _Rows([{"connector_code": "postgres", "name": "Warehouse"}]),
    ]
    assert sr.resolve_connection(conn, domain_connection_id=5, workspace_id=1) == (10, 5, "ozon", "orders")
    assert sr.resolve_connection(conn, connection_id=11, workspace_id=1) == (11, 6, "1c", "sales")
    assert sr.resolve_connection(conn, integration_code="sheet", stream_name="rows", workspace_id=1) == (12, None, "sheet", "rows")
    row = sr.attach_load_destination(conn, {"id": 1, "domain_connection_id": 6})
    assert row["load_destination"]["connector_code"] == "postgres"


def test_refresh_sync_run_status_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    # terminal branch
    conn.execute.return_value = _Rows(
        [
            {
                "id": 3,
                "workspace_id": 1,
                "connection_id": 1,
                "domain_connection_id": 1,
                "integration_code": "ozon",
                "stream_name": "orders",
                "status": "success",
                "dagster_run_id": "d-3",
                "started_at": None,
                "finished_at": datetime.now(timezone.utc),
                "triggered_by": "u",
                "error_message": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]
    )
    monkeypatch.setattr(sr, "fetch_dagster_run_status", lambda _rid: ("success", datetime.now(timezone.utc)))
    out = sr.refresh_sync_run_status(conn, {"id": 3, "status": "running", "dagster_run_id": "d-3"})
    assert out["status"] == "success"

    # unchanged / exception branch
    monkeypatch.setattr(sr, "fetch_dagster_run_status", lambda _rid: (_ for _ in ()).throw(sr.SyncRunError("x")))
    same = sr.refresh_sync_run_status(conn, {"id": 4, "status": "running", "dagster_run_id": "d-4"})
    assert same["status"] == "running"
