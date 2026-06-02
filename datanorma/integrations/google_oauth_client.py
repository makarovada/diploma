"""Загрузка OAuth client_secret JSON (без зависимости от FastAPI)."""

from __future__ import annotations

import json
from pathlib import Path

from datanorma.config import get_settings

GOOGLE_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)


def resolved_google_oauth_client_path() -> Path:
    s = get_settings()
    raw = s.datanorma_google_oauth_client_file.strip()
    if raw:
        return Path(raw)
    return s.resolved_repo_root() / "config" / "secrets" / "google_oauth_client.json"


def load_google_oauth_web_client() -> tuple[str, str]:
    path = resolved_google_oauth_client_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Файл OAuth-клиента Google не найден: {path}. "
            "Скопируйте config/secrets/google_oauth_client.json.example → google_oauth_client.json."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    block = data.get("web") or data.get("installed") or {}
    client_id = str(block.get("client_id") or "").strip()
    client_secret = str(block.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        raise ValueError(f"В {path} нет client_id/client_secret.")
    return client_id, client_secret
