"""Хеширование паролей: bcrypt; поддержка старых SHA-256 (hex) из сидов до миграции."""

from __future__ import annotations

import hashlib
import re

import bcrypt

_LEGACY_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def is_legacy_sha256_hash(stored_hash: str) -> bool:
    """True, если хеш в БД — старый SHA-256 (hex), его нужно заменить на bcrypt после входа."""
    if not stored_hash:
        return False
    return bool(_LEGACY_SHA256_HEX.match(stored_hash.strip()))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, stored_hash: str) -> bool:
    if not plain or not stored_hash:
        return False
    s = stored_hash.strip()
    if s.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), s.encode("ascii"))
        except ValueError:
            return False
    if _LEGACY_SHA256_HEX.match(s):
        return hashlib.sha256(plain.encode("utf-8")).hexdigest() == s.lower()
    return False
