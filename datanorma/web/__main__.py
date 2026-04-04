"""Запуск: python -m datanorma.web"""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("datanorma.web.main:app", host="127.0.0.1", port=8080, reload=False)
