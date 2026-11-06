import pytest

from custom_components.satel_versa.settings import parse_inputs, validate_settings

from .conftest import FORM


def test_ranges():
    assert parse_inputs("1-3, 3, 10,30") == [1, 2, 3, 10, 30]


@pytest.mark.parametrize(
    "value", ["", "0", "31", "4-2", "1-40", "-1", "1,,2", "1-2-3", "1,x", "1.5"]
)
def test_bad_ranges(value):
    with pytest.raises(ValueError):
        parse_inputs(value)


@pytest.mark.parametrize(
    "patch",
    [
        {"ethm_key": ""},
        {"ethm_key": "x" * 13},
        {"ethm_key": "ż"},
        {"panel_id": "1234"},
        {"dloadx_id": "Z" * 8},
        {"poll_interval": float("nan")},
    ],
)
def test_credentials_and_interval(patch):
    with pytest.raises(ValueError):
        validate_settings(FORM | patch)
