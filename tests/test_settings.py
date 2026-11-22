import pytest

from custom_components.satel_versa.settings import (
    parse_inputs,
    parse_outputs,
    parse_partitions,
    validate_settings,
)

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


def test_optional_outputs_and_legacy_configuration():
    assert parse_outputs(" ") == []
    assert parse_outputs("1-3,3,12") == [1, 2, 3, 12]
    assert validate_settings(FORM)["outputs"] == []
    assert validate_settings(FORM | {"outputs": "1,12"})["outputs"] == [1, 12]


@pytest.mark.parametrize("value", ["0", "13", "1-30", "3-1", "1,,2", None, [1]])
def test_invalid_output_ranges(value):
    with pytest.raises(ValueError, match="invalid_outputs"):
        parse_outputs(value)


def test_partition_selection_and_legacy_defaults():
    assert parse_partitions("") == []
    assert parse_partitions("1-2,2") == [1, 2]
    assert validate_settings(FORM)["partitions"] == []
    assert validate_settings(FORM | {"partitions": "2"})["partitions"] == [2]


@pytest.mark.parametrize("value", ["0", "3", "1-3", "2-1", None, [1]])
def test_invalid_partition_selection(value):
    with pytest.raises(ValueError, match="invalid_partitions"):
        parse_partitions(value)
