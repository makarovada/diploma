from __future__ import annotations

import json
from pathlib import Path

import pytest

from datanorma.integrations.google_oauth_client import load_google_oauth_web_client

pytestmark = pytest.mark.unit


def test_load_google_oauth_web_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret_file = tmp_path / "google_oauth_client.json"
    secret_file.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "cid.apps.googleusercontent.com",
                    "client_secret": "sec",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DATANORMA_GOOGLE_OAUTH_CLIENT_FILE", str(secret_file))
    from datanorma.config import clear_settings_cache

    clear_settings_cache()
    cid, sec = load_google_oauth_web_client()
    assert cid == "cid.apps.googleusercontent.com"
    assert sec == "sec"
    clear_settings_cache()
