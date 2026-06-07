"""Нагрузочные сценарии DataNorma API (Locust).

Запуск (после `pip install -e ".[load]"` и поднятого сервера на :8080):

    locust -f loadtests/locustfile.py --host http://127.0.0.1:8080

Переменные окружения:
    LOAD_TEST_USER      — логин (по умолчанию seed_integrator)
    LOAD_TEST_PASSWORD  — пароль (по умолчанию IntegratorDemo2026)
    LOAD_TEST_WORKSPACE — X-Workspace-Id (по умолчанию 1)
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task


def _env(name: str, default: str) -> str:
    return (os.environ.get(name) or default).strip()


class DataNormaApiUser(HttpUser):
    """Типичный интегратор: чтение каталога, источников, подключений и очереди."""

    wait_time = between(0.3, 1.5)

    def on_start(self) -> None:
        self._token: str | None = None
        self._workspace_id = _env("LOAD_TEST_WORKSPACE", "1")
        self._login()

    def _auth_headers(self) -> dict[str, str]:
        headers = {"X-Workspace-Id": self._workspace_id}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _login(self) -> None:
        username = _env("LOAD_TEST_USER", "seed_integrator")
        password = _env("LOAD_TEST_PASSWORD", "IntegratorDemo2026")
        with self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            name="/api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed: {response.status_code} {response.text[:200]}")
                return
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                response.failure("login response without access_token")
                return
            self._token = token
            response.success()

    @task(4)
    def connectors_catalog(self) -> None:
        self.client.get(
            "/api/v1/connectors/catalog",
            headers=self._auth_headers(),
            name="/api/v1/connectors/catalog",
        )

    @task(5)
    def list_sources(self) -> None:
        self.client.get(
            "/api/v1/sources",
            headers=self._auth_headers(),
            name="/api/v1/sources",
        )

    @task(5)
    def list_destinations(self) -> None:
        self.client.get(
            "/api/v1/destinations",
            headers=self._auth_headers(),
            name="/api/v1/destinations",
        )

    @task(4)
    def list_connections(self) -> None:
        self.client.get(
            "/api/v1/connections",
            headers=self._auth_headers(),
            name="/api/v1/connections",
        )

    @task(3)
    def sync_runs_recent(self) -> None:
        self.client.get(
            "/api/v1/syncs/recent?limit=20",
            headers=self._auth_headers(),
            name="/api/v1/syncs/recent",
        )

    @task(2)
    def queue_and_activity(self) -> None:
        self.client.get(
            "/api/v1/queue",
            headers=self._auth_headers(),
            name="/api/v1/queue",
        )
        self.client.get(
            "/api/v1/activity",
            headers=self._auth_headers(),
            name="/api/v1/activity",
        )

    @task(2)
    def auth_me(self) -> None:
        self.client.get(
            "/api/auth/me",
            headers=self._auth_headers(),
            name="/api/auth/me",
        )

    @task(1)
    def ui_index(self) -> None:
        self.client.get("/ui/", name="/ui/")
