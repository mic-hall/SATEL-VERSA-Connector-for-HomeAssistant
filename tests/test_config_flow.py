from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import DATA, FORM


async def test_user_configures_only_after_read(hass, mock_client):
    with patch("custom_components.satel_versa.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            "satel_versa", context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], FORM)
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["inputs"] == [1, 10]
        assert result["result"].unique_id == DATA["panel_id"]
        mock_client.connect.assert_awaited_once()
        mock_client.read_inputs.assert_awaited_once()
        mock_client.close.assert_awaited_once()
        await hass.async_block_till_done()


async def test_failed_probe_closes_and_keeps_form(hass, mock_client):
    mock_client.read_inputs.side_effect = TimeoutError
    result = await hass.config_entries.flow.async_init(
        "satel_versa", context={"source": SOURCE_USER}, data=FORM
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    mock_client.close.assert_awaited_once()


async def test_invalid_id_does_not_connect(hass, mock_client):
    result = await hass.config_entries.flow.async_init(
        "satel_versa", context={"source": SOURCE_USER}, data=FORM | {"panel_id": "1234"}
    )
    assert result["errors"] == {"base": "invalid_identifier"}
    mock_client.connect.assert_not_awaited()


async def test_duplicate_panel_does_not_connect(hass, mock_client):
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "satel_versa", context={"source": SOURCE_USER}, data=FORM
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_client.connect.assert_not_awaited()


async def test_options_validate_input_ranges(hass, mock_client):
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"inputs": "0,31", "poll_interval": 1}
    )
    assert result["errors"] == {"base": "invalid_inputs"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"inputs": "1-3,10", "poll_interval": 2}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["inputs"] == [1, 2, 3, 10]
