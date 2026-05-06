from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    subprocess.check_call(["alembic", "upgrade", "head"])
    if len(sys.argv) < 2:
        raise SystemExit("No command provided for runtime start")
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()

