"""Проверка пароля (как в сидах: SHA-256 от строки UTF-8 → hex)."""

from __future__ import annotations

import hashlib


def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_password(plain: str, stored_hash: str) -> bool:
    if not plain or not stored_hash:
        return False
    return hash_password(plain) == stored_hash.strip().lower()
