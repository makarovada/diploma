"""OAuth 2.0 Google (Sheets/Drive) для подключения источников через UI."""

from __future__ import annotations

import logging
import secrets
import threading
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from typing import Annotated, Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from datanorma.config import get_settings
from datanorma.integrations.google_oauth_client import GOOGLE_OAUTH_SCOPES, load_google_oauth_web_client
from datanorma.web.config import jwt_secret
from datanorma.web.deps import AuthUser, get_current_user

_log = logging.getLogger(__name__)

_PENDING_TTL_SEC = 600
_pending_lock = threading.Lock()
_pending_tokens: dict[str, dict[str, Any]] = {}
_completed_tokens: dict[str, dict[str, Any]] = {}


def _prune_pending() -> None:
    now = time.time()
    expired = [k for k, v in _pending_tokens.items() if now - float(v.get("created_at", 0)) > _PENDING_TTL_SEC]
    for k in expired:
        _pending_tokens.pop(k, None)
    expired_done = [k for k, v in _completed_tokens.items() if now - float(v.get("created_at", 0)) > _PENDING_TTL_SEC]
    for k in expired_done:
        _completed_tokens.pop(k, None)


def _oauth_tokens_response(entry: dict[str, Any]) -> dict[str, Any]:
    refresh = entry.get("refresh_token")
    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "no_refresh_token",
                "message": "Google не вернул refresh_token. Отзовите доступ приложению в аккаунте Google и повторите вход.",
            },
        )
    return {
        "oauth_access_token": entry.get("access_token"),
        "oauth_refresh_token": refresh,
        "oauth_token_type": entry.get("token_type"),
        "oauth_expires_in": entry.get("expires_in"),
        "oauth_scope": entry.get("scope"),
    }


def google_oauth_redirect_uri() -> str:
    s = get_settings()
    explicit = s.datanorma_google_oauth_redirect_uri.strip()
    if explicit:
        return explicit
    return "http://127.0.0.1:8080/api/v1/integrations/google/oauth/callback"


def google_oauth_frontend_return_url() -> str:
    s = get_settings()
    explicit = s.datanorma_google_oauth_frontend_return_url.strip()
    if explicit:
        return explicit.rstrip("/")
    return "http://127.0.0.1:5173"


def _allowed_return_hosts() -> set[str]:
    from datanorma.web.config import cors_allow_origins

    hosts: set[str] = {
        "127.0.0.1:5173",
        "localhost:5173",
        "127.0.0.1:8080",
        "localhost:8080",
    }
    for origin in cors_allow_origins():
        netloc = urlparse(origin).netloc
        if netloc:
            hosts.add(netloc)
    fe = urlparse(google_oauth_frontend_return_url()).netloc
    if fe:
        hosts.add(fe)
    return hosts


def _normalize_return_url(return_url: str | None, return_path: str | None) -> str:
    """Собрать безопасный return URL; для hash-SPA — `origin/#/path`."""
    raw = (return_url or "").strip()
    if not raw and return_path:
        path = return_path.strip()
        if path and not path.startswith("/"):
            path = f"/{path}"
        if path and "://" not in path:
            raw = f"{google_oauth_frontend_return_url()}/#{path}"
    if not raw:
        raw = f"{google_oauth_frontend_return_url()}/#/sources/new"
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return f"{google_oauth_frontend_return_url()}/#/sources/new"
    if parsed.netloc not in _allowed_return_hosts():
        return f"{google_oauth_frontend_return_url()}/#/sources/new"
    return raw


def _append_hash_query_param(return_url: str, key: str, value: str) -> str:
    if "#" in return_url:
        base, frag = return_url.split("#", 1)
        if "?" in frag:
            frag_path, frag_qs = frag.split("?", 1)
            pairs = list(parse_qsl(frag_qs, keep_blank_values=True))
        else:
            frag_path, pairs = frag, []
        pairs = [(k, v) for k, v in pairs if k not in ("google_oauth_state", "google_oauth_error")]
        pairs.append((key, value))
        return f"{base}#{frag_path}?{urlencode(pairs)}"
    parsed = urlparse(return_url)
    pairs = list(parse_qsl(parsed.query, keep_blank_values=True))
    pairs = [(k, v) for k, v in pairs if k not in ("google_oauth_state", "google_oauth_error")]
    pairs.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(pairs)))


def _append_google_oauth_state(return_url: str, oauth_state: str) -> str:
    return _append_hash_query_param(return_url, "google_oauth_state", oauth_state)


def _make_oauth_state(username: str, *, return_url: str) -> str:
    now = int(time.time())
    payload = {
        "purpose": "google_oauth",
        "sub": username,
        "nonce": secrets.token_urlsafe(16),
        "return_url": return_url,
        "iat": now,
        "exp": now + _PENDING_TTL_SEC,
    }
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")


def _decode_oauth_state(state: str, *, expected_username: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(state, jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_oauth_state"}) from exc
    if payload.get("purpose") != "google_oauth":
        raise HTTPException(status_code=400, detail={"error_code": "invalid_oauth_state"})
    if expected_username is not None and payload.get("sub") != expected_username:
        raise HTTPException(status_code=403, detail={"error_code": "oauth_state_user_mismatch"})
    return payload


def build_google_authorization_url(*, state: str) -> str:
    client_id, _secret = load_google_oauth_web_client()
    params = {
        "client_id": client_id,
        "redirect_uri": google_oauth_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(GOOGLE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)


def exchange_authorization_code(code: str) -> dict[str, Any]:
    client_id, client_secret = load_google_oauth_web_client()
    redirect_uri = google_oauth_redirect_uri()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code >= 400:
        _log.warning("Google token exchange failed: %s %s", resp.status_code, resp.text[:500])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "google_token_exchange_failed", "message": resp.text[:300]},
        )
    data = resp.json()
    if not data.get("refresh_token"):
        _log.warning("Google token response without refresh_token (повторите с prompt=consent)")
    return data


def register_google_oauth_routes(v1: APIRouter) -> None:
    @v1.get("/integrations/google/oauth/start")
    def google_oauth_start(
        user: Annotated[AuthUser, Depends(get_current_user)],
        return_url: str | None = Query(None, max_length=2000),
        return_path: str | None = Query(None, max_length=500),
    ) -> dict[str, Any]:
        safe_return = _normalize_return_url(return_url, return_path)
        try:
            state = _make_oauth_state(user.username, return_url=safe_return)
            url = build_google_authorization_url(state=state)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "google_oauth_not_configured", "message": str(exc)},
            ) from exc
        return {"authorization_url": url, "state": state}

    @v1.get("/integrations/google/oauth/callback", include_in_schema=False)
    def google_oauth_callback(
        code: str | None = Query(None),
        state: str | None = Query(None),
        error: str | None = Query(None),
    ) -> RedirectResponse:
        fallback = f"{google_oauth_frontend_return_url()}/#/sources/new"
        if error:
            return RedirectResponse(url=_append_hash_query_param(fallback, "google_oauth_error", error))
        if not code or not state:
            return RedirectResponse(
                url=_append_hash_query_param(fallback, "google_oauth_error", "missing_code_or_state")
            )
        try:
            state_payload = _decode_oauth_state(state)
            token_data = exchange_authorization_code(code)
            stored_return = str(state_payload.get("return_url") or "").strip()
            if not stored_return:
                legacy_path = str(state_payload.get("return_path") or "/sources/new")
                stored_return = _normalize_return_url(None, legacy_path)
        except HTTPException:
            return RedirectResponse(url=_append_hash_query_param(fallback, "google_oauth_error", "exchange_failed"))
        except Exception as exc:
            _log.exception("google oauth callback: %s", exc)
            return RedirectResponse(url=_append_hash_query_param(fallback, "google_oauth_error", "internal"))

        with _pending_lock:
            _prune_pending()
            _pending_tokens[state] = {
                "created_at": time.time(),
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "token_type": token_data.get("token_type"),
                "scope": token_data.get("scope"),
            }

        return RedirectResponse(url=_append_google_oauth_state(stored_return, state))

    @v1.get("/integrations/google/oauth/complete")
    def google_oauth_complete(
        state: str,
        user: Annotated[AuthUser, Depends(get_current_user)],
    ) -> dict[str, Any]:
        _decode_oauth_state(state, expected_username=user.username)
        with _pending_lock:
            _prune_pending()
            if state in _completed_tokens:
                return _oauth_tokens_response(_completed_tokens[state])
            entry = _pending_tokens.pop(state, None)
            if entry is not None:
                _completed_tokens[state] = entry
        if entry is None:
            raise HTTPException(status_code=404, detail={"error_code": "oauth_session_not_found"})
        return _oauth_tokens_response(entry)
