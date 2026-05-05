import pytest

from datanorma.normalization.rules import ColumnRule, StreamRules
from datanorma.warehouse.tables import ensure_normalized_table, validate_stream_rules_compatible


def test_add_column_allowed():
    old_rules = StreamRules(
        stream_name="orders",
        columns=[ColumnRule(source_field="id", target_field="id", type="integer")],
    )
    new_rules = StreamRules(
        stream_name="orders",
        columns=[
            ColumnRule(source_field="id", target_field="id", type="integer"),
            ColumnRule(source_field="name", target_field="name", type="string"),
        ],
    )
    validate_stream_rules_compatible(old_rules, new_rules)
    table = ensure_normalized_table(connector_code="ozon", stream_rules=new_rules)
    assert "name" in table.c


def test_type_change_requires_recreate_stream():
    old_rules = StreamRules(
        stream_name="orders",
        columns=[ColumnRule(source_field="amount", target_field="amount", type="integer")],
    )
    new_rules = StreamRules(
        stream_name="orders",
        columns=[ColumnRule(source_field="amount", target_field="amount", type="number")],
    )
    with pytest.raises(ValueError, match="recreate stream required"):
        validate_stream_rules_compatible(old_rules, new_rules)
