"""httpx wrapper: timeouts and retries on 429 / 5xx."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

_log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 4


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | list[Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> tuple[int, Any]:
    """HTTP JSON request. Returns (status_code, parsed_json_or_text_dict).

    Retries on HTTP 429 and 5xx with exponential backoff (0.5s, 1s, 2s, …).
    """
    hdrs = dict(headers or {})
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.request(
                    method.upper(),
                    url,
                    headers=hdrs,
                    params=params,
                    json=json_body,
                )
            if r.status_code == 429 or r.status_code >= 500:
                wait = 0.5 * (2**attempt)
                _log.warning("HTTP %s %s → %s, retry in %.1fs", method, url, r.status_code, wait)
                time.sleep(wait)
                continue
            ct = r.headers.get("content-type", "")
            if "application/json" in ct.lower():
                return r.status_code, r.json()
            return r.status_code, {"_raw_text": r.text[:8000]}
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            wait = 0.5 * (2**attempt)
            _log.warning("HTTP %s %s transport error: %s; retry in %.1fs", method, url, exc, wait)
            time.sleep(wait)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"HTTP request failed after retries: {method} {url}")
