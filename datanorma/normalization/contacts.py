"""Нормализация телефона (РФ → E.164 +7) и email."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def normalize_phone_ru(raw: str | None) -> str | None:
    """Привести российский номер к виду +7XXXXXXXXXX (10 цифр после 7)."""
    if raw is None:
        return None
    s = re.sub(r"[^\d+]", "", str(raw).strip())
    if not s:
        return None
    if s.startswith("+"):
        digits = re.sub(r"\D", "", s)
        if digits.startswith("7") and len(digits) == 11:
            return "+7" + digits[1:]
        if digits.startswith("8") and len(digits) == 11:
            return "+7" + digits[1:]
        return None
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits.startswith("8"):
        return "+7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return None


def normalize_email(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    if not _EMAIL_RE.match(s):
        return None
    return s
