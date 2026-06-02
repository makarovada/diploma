"""Фоновый планировщик cron-синхронизаций connection (работает в процессе FastAPI)."""

from __future__ import annotations

import logging
import os
import threading
import time

from sqlalchemy import create_engine

from datanorma.config import get_settings
from datanorma.schedules.connection_cron_runner import run_due_scheduled_syncs

_log = logging.getLogger(__name__)

_THREAD: threading.Thread | None = None
_STOP = threading.Event()
_INTERVAL_SECONDS = 60


def _scheduler_enabled() -> bool:
    raw = (os.environ.get("DATANORMA_CONNECTION_SCHEDULER") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _scheduler_loop() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    fired: dict[str, str] = {}
    _log.info("Connection cron scheduler started (interval=%ss)", _INTERVAL_SECONDS)

    while not _STOP.wait(_INTERVAL_SECONDS):
        try:
            count, errors, fired = run_due_scheduled_syncs(engine, fired=fired)
            if count:
                _log.info("Scheduled ELT sync triggered for %s connection(s)", count)
            for err in errors[:5]:
                _log.error("Scheduled sync error: %s", err)
        except Exception:
            _log.exception("Connection cron scheduler tick failed")


def start_connection_scheduler() -> None:
    global _THREAD
    if not _scheduler_enabled():
        _log.info("Connection cron scheduler disabled (DATANORMA_CONNECTION_SCHEDULER)")
        return
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_scheduler_loop, name="connection-cron", daemon=True)
    _THREAD.start()


def stop_connection_scheduler() -> None:
    _STOP.set()
