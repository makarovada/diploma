from __future__ import annotations

from pathlib import Path


INTEGRATION_HINTS = (
    "_api",
    "pipeline",
    "warehouse",
    "raw_staging",
    "sync_runs",
    "destination_write",
)


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        if any(item.iter_markers(name=m) for m in ("unit", "integration", "e2e")):
            continue

        name = Path(item.nodeid).name.lower()
        if any(h in name for h in INTEGRATION_HINTS):
            item.add_marker("integration")
        else:
            item.add_marker("unit")
