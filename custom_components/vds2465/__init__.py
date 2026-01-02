import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_PORT
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN, CONF_DEVICES, EVENT_VDS_ALARM
from .vds_lib import VdSAsyncServer

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor", "switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VdS 2465 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    port = entry.data.get(CONF_PORT)
    devices_raw = entry.options.get(CONF_DEVICES, {})

    # Cleanup orphaned devices BEFORE starting server
    # This ensures that even if the server fails to bind (re-load issue), 
    # the device registry is kept in sync with config.
    device_registry = dr.async_get(hass)
    device_entries = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    current_ident_nrs = {str(d["identnr"]) for d in devices_raw.values()}
    
    for dev_entry in device_entries:
        for domain, ident in dev_entry.identifiers:
            if domain == DOMAIN and ident not in current_ident_nrs:
                _LOGGER.debug(f"Removing orphaned device: {ident}")
                device_registry.async_remove_device(dev_entry.id)
                break
    
    # Baue Map für die Lib: KeyNr -> Config (nur für verschlüsselte Geräte nötig)
    devices_config_lib = {}
    for dev in devices_raw.values():
        # Nur wenn verschlüsselt und KeyNr vorhanden
        if dev.get("encrypted", True) and dev.get("keynr"):
            try:
                k_nr = int(dev["keynr"])
                if k_nr > 0:
                    devices_config_lib[k_nr] = dev
            except ValueError:
                pass

    hub = VdsHub(hass, port, devices_config_lib)
    
    # Start Server Task
    try:
        await hub.start()
        hass.data[DOMAIN][entry.entry_id] = hub
    except Exception as e:
        _LOGGER.error(f"Failed to start VdS Server: {e}")
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading VdS Entry...")
    hub = hass.data[DOMAIN].get(entry.entry_id)
    if hub:
        _LOGGER.debug("Stopping VdS Hub...")
        try:
            await hub.stop()
            _LOGGER.debug("VdS Hub stopped.")
        except Exception as e:
             _LOGGER.error(f"Error stopping VdS Hub: {e}")
        
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug(f"Platforms unloaded: {unload_ok}")
    
    if unload_ok:
        del hass.data[DOMAIN][entry.entry_id]

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class VdsHub:
    """Hub to handle VdS Server and entity callbacks."""
    def __init__(self, hass, port, devices_config):
        self.hass = hass
        self.port = port
        self.devices_config = devices_config
        self.server = VdSAsyncServer("0.0.0.0", port, devices_config, self.handle_vds_event)
        self._listeners = []

    async def start(self):
        await self.server.start()

    async def stop(self):
        await self.server.stop()

    def handle_vds_event(self, event_type, data):
        """Callback from VdS Lib."""
        # 1. Fire generic event to HA Bus
        event_payload = {"type": event_type, **data}
        _LOGGER.debug(f"VdS Event: {event_type} - {data}")
        self.hass.bus.async_fire(EVENT_VDS_ALARM, event_payload)

        # 2. Notify entities
        for listener in self._listeners:
            listener(event_type, data)

    def add_listener(self, callback_func):
        self._listeners.append(callback_func)
        return lambda: self._listeners.remove(callback_func)

    def send_output(self, identnr, address, state, device=1, area=1):
        """Send output command to a specific device."""
        if not self.server.send_output_command(identnr, address, state, device, area):
            _LOGGER.warning(f"Could not send output command to {identnr}: Device not connected")
