import pytest


@pytest.mark.unit
def test_unit_marker_smoke():
    assert True


@pytest.mark.integration
def test_integration_marker_smoke():
    assert True
