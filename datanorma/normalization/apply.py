"""Применение StreamRules к строкам raw-слоя."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datanorma.normalization.rules import StreamRules
from datanorma.normalization.typing import cast_row


@dataclass(slots=True)
class NormStats:
    """Статистика применения нормализации к батчу."""

    rows_in: int = 0
    rows_out: int = 0
    issues: int = 0
    dropped_rows: int = 0


def apply_rules_to_row(rule_set: StreamRules, row: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Применить правила к одной строке."""
    return cast_row(rule_set, row)


def apply_rules_to_batch(rule_set: StreamRules, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], NormStats]:
    """Применить правила к батчу строк."""
    stats = NormStats(rows_in=len(rows))
    normalized: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen_keys: set[tuple[Any, ...]] = set()

    for row in rows:
        norm_row, row_issues = apply_rules_to_row(rule_set, row)
        if row_issues and any(i.get("error_code") == "required_missing" for i in row_issues):
            stats.dropped_rows += 1
            issues.extend(row_issues)
            continue
        if rule_set.deduplicate and rule_set.primary_key:
            key = tuple(norm_row.get(pk) for pk in rule_set.primary_key)
            if all(v is not None for v in key):
                if key in seen_keys:
                    stats.dropped_rows += 1
                    continue
                seen_keys.add(key)
        normalized.append(norm_row)
        issues.extend(row_issues)

    stats.rows_out = len(normalized)
    stats.issues = len(issues)
    return normalized, issues, stats
