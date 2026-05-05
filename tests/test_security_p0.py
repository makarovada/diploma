"""Security P0: JWT и CORS в production, без небезопасных дефолтов."""

from __future__ import annotations

import pytest

from datanorma.config import clear_settings_cache
from datanorma.web.main import create_app

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    clear_settings_cache()


def test_production_requires_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("DATANORMA_ENVIRONMENT", "production")
    monkeypatch.delenv("DATANORMA_JWT_SECRET", raising=False)
    monkeypatch.delenv("DATANORMA_CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="DATANORMA_JWT_SECRET"):
        create_app()


def test_production_rejects_dev_jwt_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("DATANORMA_ENVIRONMENT", "production")
    monkeypatch.setenv("DATANORMA_JWT_SECRET", "dev-insecure-change-me")
    monkeypatch.setenv("DATANORMA_CORS_ORIGINS", "https://app.example.com")
    with pytest.raises(RuntimeError, match="заглушку"):
        create_app()


def test_production_requires_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("DATANORMA_ENVIRONMENT", "production")
    monkeypatch.setenv("DATANORMA_JWT_SECRET", "a-secure-enough-secret-for-production-test-32chars")
    monkeypatch.delenv("DATANORMA_CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="DATANORMA_CORS_ORIGINS"):
        create_app()


def test_production_starts_with_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("DATANORMA_ENVIRONMENT", "production")
    monkeypatch.setenv("DATANORMA_JWT_SECRET", "a-secure-enough-secret-for-production-test-32chars")
    monkeypatch.setenv("DATANORMA_CORS_ORIGINS", "https://app.example.com")
    app = create_app()
    assert app.title == "DataNorma"
