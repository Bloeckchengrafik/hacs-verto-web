"""Load the integration through the real HA flow and platform machinery."""

import pytest
from aiohttp import ThreadedResolver, web
from homeassistant import loader
from homeassistant.bootstrap import async_load_base_functionality
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.verto_web.const import ENDPOINTS


@pytest.mark.asyncio
async def test_real_setup_and_unload(aiohttp_server, tmp_path, payloads, monkeypatch):
    async def handler(request):
        key = next(key for key, path in ENDPOINTS.items() if path == request.path)
        return web.json_response(payloads[key])

    app = web.Application()
    app.router.add_get("/{tail:.*}", handler)
    server = await aiohttp_server(app)
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config_entries = ConfigEntries(hass, {})
    await async_load_base_functionality(hass)
    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client._async_make_resolver", lambda hass: ThreadedResolver()
    )
    try:
        result = await hass.config_entries.flow.async_init(
            "verto_web",
            context={"source": "user"},
            data={"host": str(server.make_url("/"))},
        )
        assert result["type"] == "create_entry"
        await hass.async_block_till_done()
        entry = result["result"]
        assert entry.state.value == "loaded"
        assert hass.states.get("sensor.fronius_verto_load_power").state == "574.2786425"
        assert hass.states.get("binary_sensor.fronius_verto_backup_mode").state == "off"
        entities = er.async_get(hass).entities
        assert any(
            entity.disabled_by
            for entity in entities.values()
            if "FUTURE_UNKNOWN_CHANNEL" in entity.unique_id
        )
        duplicate = await hass.config_entries.flow.async_init(
            "verto_web",
            context={"source": "user"},
            data={"host": str(server.make_url("/"))},
        )
        assert duplicate["type"] == "abort" and duplicate["reason"] == "already_configured"
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.fronius_verto_load_power").state == "unavailable"
    finally:
        await hass.async_stop()
