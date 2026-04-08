"""Post-load dbt transformation."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import dagster as dg
import yaml

from datanorma.config import get_settings

try:
    from dagster_dbt import DbtCliResource
except Exception:  # pragma: no cover - optional import
    DbtCliResource = None  # type: ignore[assignment]


def _write_temp_profile(profile_dir: Path) -> Path:
    settings = get_settings()
    raw = os.environ.get("DBT_DATABASE_URL", settings.database_url)
    normalized = raw.replace("postgresql+psycopg://", "postgres://").replace("postgresql://", "postgres://")
    u = urlparse(normalized)
    payload = {
        "datanorma": {
            "target": "dev",
            "outputs": {
                "dev": {
                    "type": "postgres",
                    "host": u.hostname or "127.0.0.1",
                    "user": u.username or "postgres",
                    "password": u.password or "",
                    "port": u.port or 5432,
                    "dbname": (u.path or "/postgres").lstrip("/"),
                    "schema": "public",
                    "threads": 4,
                }
            },
        }
    }
    out = profile_dir / "profiles.yml"
    out.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return out


@dg.asset(
    group_name="warehouse",
    description="dbt Core post-load transformation (models in /dbt/models).",
)
def dbt_run(warehouse_sales: dict) -> dict:
    _ = warehouse_sales
    settings = get_settings()
    project_dir = settings.resolved_dbt_project_dir()
    if not project_dir.is_dir():
        return {"status": "skipped", "reason": f"dbt project dir not found: {project_dir}"}

    cmd = ["dbt", "run", "--project-dir", str(project_dir)]
    if DbtCliResource is not None:
        profiles_env = os.environ.get("DBT_PROFILES_DIR", "").strip()
        if profiles_env:
            resource = DbtCliResource(project_dir=str(project_dir), profiles_dir=profiles_env)
            inv = resource.cli(["run"])
            result = inv.wait()
            return {"status": "ok" if result.success else "failed", "via": "dagster-dbt"}
        with tempfile.TemporaryDirectory(prefix="datanorma_dbt_profiles_") as tmp:
            tmp_dir = Path(tmp)
            _write_temp_profile(tmp_dir)
            resource = DbtCliResource(project_dir=str(project_dir), profiles_dir=str(tmp_dir))
            inv = resource.cli(["run"])
            result = inv.wait()
            return {"status": "ok" if result.success else "failed", "via": "dagster-dbt"}

    profiles_env = os.environ.get("DBT_PROFILES_DIR", "").strip()
    if profiles_env:
        cmd.extend(["--profiles-dir", profiles_env])
        run = subprocess.run(cmd, capture_output=True, text=True, check=False)
    else:
        with tempfile.TemporaryDirectory(prefix="datanorma_dbt_profiles_") as tmp:
            tmp_dir = Path(tmp)
            _write_temp_profile(tmp_dir)
            cmd.extend(["--profiles-dir", str(tmp_dir)])
            run = subprocess.run(cmd, capture_output=True, text=True, check=False)

    return {
        "status": "ok" if run.returncode == 0 else "failed",
        "returncode": run.returncode,
        "stdout_tail": "\n".join((run.stdout or "").splitlines()[-40:]),
        "stderr_tail": "\n".join((run.stderr or "").splitlines()[-40:]),
    }
