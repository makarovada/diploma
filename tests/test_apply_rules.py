from datanorma.normalization.apply import apply_rules_to_batch
from datanorma.normalization.rules import ColumnRule, StreamRules


def test_apply_rules_to_batch_handles_required_and_cast_errors():
    rules = StreamRules(
        stream_name="orders",
        primary_key=["id"],
        columns=[
            ColumnRule(source_field="id", target_field="id", type="integer", required=True),
            ColumnRule(source_field="email", target_field="email", type="email", required=True),
            ColumnRule(source_field="status", target_field="status", type="enum", enum_map={"ok": "ok"}),
        ],
    )
    rows = [
        {"id": "1", "email": "a@test.local", "status": "ok"},
        {"id": "2", "email": "", "status": "ok"},
        {"id": "3", "email": "bad-email", "status": "missing"},
    ]
    normalized, issues, stats = apply_rules_to_batch(rules, rows)
    assert len(normalized) == 2
    assert stats.rows_in == 3
    assert stats.rows_out == 2
    assert len(issues) >= 2
