from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import DATA, FORM


async def loaded_entry(hass):
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_reconfigure_reloads_with_new_host(hass, mock_client):
    entry = await loaded_entry(hass)
    result = await hass.config_entries.flow.async_init(
        "satel_versa", context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], FORM | {"host": "192.0.2.20"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "192.0.2.20"
    await hass.async_block_till_done()
    mock_client.close.assert_awaited()
    await hass.config_entries.async_unload(entry.entry_id)


async def test_reconfigure_cannot_change_panel_identity(hass, mock_client):
    entry = await loaded_entry(hass)
    calls = mock_client.connect.await_count
    result = await hass.config_entries.flow.async_init(
        "satel_versa",
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        data=FORM | {"panel_id": "01020305"},
    )
    assert result["errors"] == {"base": "wrong_panel"}
    assert entry.data["panel_id"] == DATA["panel_id"]
    assert mock_client.connect.await_count == calls
    await hass.config_entries.async_unload(entry.entry_id)
