"""Запуск: python -m datanorma.web"""

from __future__ import annotations

import argparse
import os

import uvicorn


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DataNorma web server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode (uvicorn reload)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Force uvicorn reload mode",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    env_dev = os.getenv("DATANORMA_DEV", "").strip().lower() in {"1", "true", "yes", "on"}
    use_reload = bool(args.dev or args.reload or env_dev)
    uvicorn.run("datanorma.web.main:app", host=args.host, port=args.port, reload=use_reload)
