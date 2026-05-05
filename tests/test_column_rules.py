from datanorma.normalization.rules import ColumnRule
from datanorma.normalization.typing import cast_value


def test_cast_value_string():
    rule = ColumnRule(source_field="name", target_field="name", type="string")
    value, issue = cast_value(rule, "  Ivan  ")
    assert value == "Ivan"
    assert issue is None


def test_cast_value_number_with_separators():
    rule = ColumnRule(
        source_field="amount",
        target_field="amount",
        type="number",
        decimal_separator=",",
        thousands_separator=" ",
    )
    value, issue = cast_value(rule, "12 345,50")
    assert str(value) == "12345.50"
    assert issue is None


def test_cast_value_required_missing_creates_issue():
    rule = ColumnRule(source_field="email", target_field="email", type="email", required=True)
    value, issue = cast_value(rule, "")
    assert value is None
    assert issue is not None
    assert issue["error_code"] == "required_missing"
