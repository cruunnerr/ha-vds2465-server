import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_PORT
from homeassistant.helpers import device_registry as dr, entity_registry as er
from .const import DOMAIN, CONF_DEVICES, EVENT_VDS_ALARM, CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
from .vds_lib import VdSAsyncServer

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor", "switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VdS 2465 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Port and Interval can be in data (initial) or options (updates)
    port = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT))
    interval = entry.options.get(CONF_POLLING_INTERVAL, entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL))
    
    devices_raw = entry.options.get(CONF_DEVICES, {})
    current_ident_nrs = {str(d["identnr"]) for d in devices_raw.values()}

    # 1. Cleanup orphaned devices from Device Registry
    device_registry = dr.async_get(hass)
    device_entries = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    
    for dev_entry in device_entries:
        for domain, ident in dev_entry.identifiers:
            if domain == DOMAIN and ident not in current_ident_nrs:
                _LOGGER.info(f"Removing orphaned VdS device from registry: {ident}")
                device_registry.async_remove_device(dev_entry.id)
                break

    # 2. Cleanup orphaned entities from Entity Registry
    entity_registry = er.async_get(hass)
    entity_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    for ent_entry in entity_entries:
        # Check if the entity is associated with an identnr that no longer exists
        # We look for the identnr in the unique_id (common pattern in this component) 
        # OR we check if its device is gone.
        
        # Check if device_id is still in the device registry (if it had one)
        if ent_entry.device_id:
            if device_registry.async_get(ent_entry.device_id) is None:
                _LOGGER.info(f"Removing orphaned VdS entity (no device): {ent_entry.entity_id}")
                entity_registry.async_remove_entry(ent_entry.entity_id)
                continue

        # Check unique_id for identnr (failsafe)
        # Unique IDs are usually vds_[ident]_... or similar
        for ident in current_ident_nrs:
            if ident in ent_entry.unique_id:
                break
        else:
            # No current identnr found in unique_id, and it belongs to our entry
            _LOGGER.info(f"Removing orphaned VdS entity (no config): {ent_entry.entity_id}")
            entity_registry.async_remove_entry(ent_entry.entity_id)
    
    devices_config_list = list(devices_raw.values())

    hub = VdsHub(hass, port, interval, devices_config_list)
    
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
    def __init__(self, hass, port, interval, devices_config):
        self.hass = hass
        self.port = port
        self.interval = interval
        self.devices_config = devices_config
        self.server = VdSAsyncServer("0.0.0.0", port, devices_config, self.handle_vds_event, interval)
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
