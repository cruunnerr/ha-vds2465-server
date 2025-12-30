from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICES

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VdS binary sensors."""
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = entry.options.get(CONF_DEVICES, {})

    entities = []
    for key_nr, dev_conf in devices.items():
        entities.append(VdsConnectivitySensor(hub, key_nr, dev_conf))

    async_add_entities(entities)


class VdsConnectivitySensor(BinarySensorEntity):
    """Binary Sensor representing connection status of a VdS device."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False

    def __init__(self, hub, key_nr, dev_conf):
        self._hub = hub
        self._key_nr = int(key_nr)
        self._ident_nr = dev_conf.get("identnr", "Unknown")
        self._attr_name = f"VdS {self._ident_nr} Status"
        self._attr_unique_id = f"vds_status_{self._key_nr}"
        self._attr_is_on = False
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._key_nr))},
            "name": f"VdS Device {self._ident_nr}",
            "manufacturer": "VdS 2465",
            "model": "Generic ID",
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        # Check if event is for this device
        event_key = data.get("keynr")
        if event_key != self._key_nr:
            return

        if event_type == "connected":
            self._attr_is_on = True
            self.async_write_ha_state()
        elif event_type == "disconnected":
            self._attr_is_on = False
            self.async_write_ha_state()
