"""Курсы валют ЦБ РФ (ежедневный XML), кэш по календарной дате."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

import httpx

MSK = ZoneInfo("Europe/Moscow")
CBR_DAILY_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


def _date_req_param(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def parse_cbr_daily_xml(xml_text: str) -> dict[str, float]:
    """CharCode (USD, EUR, …) → сколько рублей за 1 единицу валюты с учётом Nominal."""
    root = ET.fromstring(xml_text)
    rates: dict[str, float] = {}
    for node in root.findall("Valute"):
        code_el = node.find("CharCode")
        val_el = node.find("Value")
        nom_el = node.find("Nominal")
        if code_el is None or val_el is None or nom_el is None:
            continue
        code = (code_el.text or "").strip()
        raw_val = (val_el.text or "0").replace(",", ".")
        try:
            value = float(raw_val)
            nominal = int((nom_el.text or "1").strip())
        except ValueError:
            continue
        if nominal <= 0:
            continue
        rates[code] = value / nominal
    return rates


@lru_cache(maxsize=64)
def _fetch_cbr_rates_cached(y: int, m: int, day: int) -> frozenset[tuple[str, float]]:
    d = date(y, m, day)
    params = {"date_req": _date_req_param(d)}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(CBR_DAILY_URL, params=params)
        r.raise_for_status()
    rates = parse_cbr_daily_xml(r.text)
    return frozenset(rates.items())


def get_cbr_rates_map(for_date: date) -> dict[str, float]:
    """Словарь курсов на указанную дату (публикация ЦБ на этот день). При ошибке сети — {}."""
    try:
        items = _fetch_cbr_rates_cached(for_date.year, for_date.month, for_date.day)
        return dict(items)
    except (httpx.HTTPError, OSError, ET.ParseError, ValueError):
        return {}


def today_msk() -> date:
    return datetime.now(MSK).date()


def coerce_currency_code(code: Any) -> str | None:
    if code is None or code == "":
        return None
    s = str(code).strip().upper()
    if s in {"RUB", "₽", "РУБ"}:
        return "RUB"
    return s


def amount_to_rub(
    amount: float | None,
    currency_code: str | None,
    rates: dict[str, float],
) -> float | None:
    if amount is None:
        return None
    cc = coerce_currency_code(currency_code)
    if cc is None or cc == "RUB":
        return float(amount)
    rate = rates.get(cc)
    if rate is None:
        return None
    return float(amount) * rate
