"""Хеши паролей: bcrypt и миграция с legacy SHA-256 (hex)."""

from __future__ import annotations

import hashlib

import pytest
from datanorma.web.passwords import hash_password, is_legacy_sha256_hash, verify_password

pytestmark = pytest.mark.unit


def test_bcrypt_round_trip() -> None:
    h = hash_password("SecretPass2026")
    assert h.startswith("$2")
    assert verify_password("SecretPass2026", h) is True
    assert verify_password("wrong", h) is False


def test_legacy_sha256_verify() -> None:
    plain = "LegacyDemo2026"
    legacy = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    assert is_legacy_sha256_hash(legacy) is True
    assert verify_password(plain, legacy) is True
    assert verify_password("nope", legacy) is False


def test_bcrypt_hash_not_legacy() -> None:
    h = hash_password("x")
    assert is_legacy_sha256_hash(h) is False


def test_is_legacy_rejects_non_hex() -> None:
    assert is_legacy_sha256_hash("not-a-hash") is False
    assert is_legacy_sha256_hash("") is False
