import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PORT
from .const import DOMAIN, CONF_DEVICES, EVENT_VDS_ALARM
from .vds_lib import VdSAsyncServer

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [] # Wir nutzen aktuell nur Events, keine Entitäten-Plattformen zwingend

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VdS 2465 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    port = entry.data.get(CONF_PORT)
    # Geräte kommen aus den Options, fallback auf leeres Dict
    devices_raw = entry.options.get(CONF_DEVICES, {})
    
    # Konvertiere Keys von String (JSON) zurück zu Int für die Lib
    devices_config = {}
    for k, v in devices_raw.items():
        devices_config[int(k)] = v

    def handle_vds_event(event_type, data):
        """Callback from VdS Lib to HA Event Bus."""
        event_payload = {"type": event_type, **data}
        _LOGGER.debug(f"Firing event {EVENT_VDS_ALARM}: {event_payload}")
        hass.bus.async_fire(EVENT_VDS_ALARM, event_payload)

    server = VdSAsyncServer("0.0.0.0", port, devices_config, handle_vds_event)

    # Start Server Task
    try:
        await server.start()
        hass.data[DOMAIN][entry.entry_id] = server
    except Exception as e:
        _LOGGER.error(f"Failed to start VdS Server: {e}")
        return False

    # Listener für Options-Änderungen (Geräte hinzufügen/entfernen)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    server = hass.data[DOMAIN].get(entry.entry_id)
    if server:
        await server.stop()
        del hass.data[DOMAIN][entry.entry_id]

    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
