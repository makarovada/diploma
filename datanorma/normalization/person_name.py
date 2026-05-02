"""Нормализация ФИО: разбор строки, регистр, целевой порядок фамилия–имя–отчество."""

from __future__ import annotations

import re
from typing import Any

# Типичное русское отчество
_PATRONYMIC_RE = re.compile(
    r"^(?P<rest>.+)(ович|овна|евич|евна|ич|инична|ыч)$",
    re.IGNORECASE,
)


def _title_ru_token(s: str) -> str:
    if not s:
        return s
    # Простая title-case по пробелам/дефисам (Иванов-Петров)
    parts = re.split(r"([\s\-]+)", s.strip())
    out: list[str] = []
    for p in parts:
        if not p or p.isspace() or p == "-":
            out.append(p)
            continue
        if len(p) == 1:
            out.append(p.upper())
        else:
            out.append(p[0].upper() + p[1:].lower())
    return "".join(out)


def parse_person_name(raw: str | None) -> dict[str, Any]:
    """Разбор полного ФИО в компоненты.

    Возвращает person_full_name, person_family_name, person_given_name, person_patronymic, quality.
    quality: full | partial | unknown
    """
    if raw is None:
        return {
            "person_full_name": None,
            "person_family_name": None,
            "person_given_name": None,
            "person_patronymic": None,
            "quality": "unknown",
        }
    s = str(raw).strip()
    if not s:
        return {
            "person_full_name": None,
            "person_family_name": None,
            "person_given_name": None,
            "person_patronymic": None,
            "quality": "unknown",
        }

    sl = s.lower()
    if any(x in sl for x in ("ооо", "ип ", "ип,", "llc", "ltd", "«", "»")):
        return {
            "person_full_name": _title_ru_token(s),
            "person_family_name": None,
            "person_given_name": None,
            "person_patronymic": None,
            "quality": "unknown",
        }

    # Убрать лишние пробелы
    tokens = [t for t in re.split(r"\s+", s) if t]
    if not tokens:
        return {
            "person_full_name": None,
            "person_family_name": None,
            "person_given_name": None,
            "person_patronymic": None,
            "quality": "unknown",
        }

    family: str | None = None
    given: str | None = None
    patronymic: str | None = None
    quality = "partial"

    if len(tokens) >= 3:
        # Фамилия Имя Отчество (стандарт РФ)
        family, given, patronymic = tokens[0], tokens[1], " ".join(tokens[2:])
        if _PATRONYMIC_RE.match(patronymic or ""):
            quality = "full"
        else:
            quality = "partial"
    elif len(tokens) == 2:
        a, b = tokens[0], tokens[1]
        if _PATRONYMIC_RE.match(b):
            given, patronymic = a, b
            quality = "partial"
        elif _PATRONYMIC_RE.match(a):
            # редко: отчество первым
            patronymic, given = a, b
            quality = "partial"
        else:
            # Имя Фамилия (западный порядок) → унифицируем в Фамилия Имя
            given, family = a, b
            quality = "partial"
    else:
        # одно слово — только имя или фамилия
        given = tokens[0]
        quality = "partial"

    def _t(x: str | None) -> str | None:
        return _title_ru_token(x) if x else None

    pat_clean = patronymic.strip() if patronymic else None
    family_t, given_t, pat_t = _t(family), _t(given), _t(pat_clean)
    parts = [p for p in (family_t, given_t, pat_t) if p]
    full = " ".join(parts) if parts else _title_ru_token(s)

    return {
        "person_full_name": full,
        "person_family_name": family_t,
        "person_given_name": given_t,
        "person_patronymic": pat_t,
        "quality": quality,
    }
