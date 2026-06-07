from __future__ import annotations

from pathlib import Path

try:
    import allure
except ImportError:  # pragma: no cover - optional dev dependency
    allure = None  # type: ignore[assignment]


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


def pytest_runtest_setup(item) -> None:
    if allure is None:
        return

    module_stem = Path(str(item.fspath)).stem
    if module_stem.startswith("test_"):
        allure.dynamic.feature(module_stem.removeprefix("test_").replace("_", " "))

    allure.dynamic.epic("datanorma")

    for marker_name in ("unit", "integration", "e2e"):
        if item.get_closest_marker(marker_name):
            allure.dynamic.parent_suite(marker_name)
            allure.dynamic.tag(marker_name)
            break
