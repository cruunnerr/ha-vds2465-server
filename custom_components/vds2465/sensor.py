from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_DEVICES

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VdS sensors."""
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = entry.options.get(CONF_DEVICES, {})

    entities = []
    for dev_conf in devices.values():
        entities.append(VdsLastMessageSensor(hub, dev_conf))
        entities.append(VdsLastTestMessageSensor(hub, dev_conf))
        entities.append(VdsManufacturerSensor(hub, dev_conf))

    async_add_entities(entities)


class VdsLastMessageSensor(SensorEntity):
    """Sensor showing the last message from a VdS device."""

    _attr_should_poll = False
    _attr_icon = "mdi:message-text-clock"

    def __init__(self, hub, dev_conf):
        self._hub = hub
        self._ident_nr = dev_conf.get("identnr", "Unknown")
        self._attr_unique_id = f"vds_last_msg_{self._ident_nr}"
        self._attr_name = f"VdS {self._ident_nr} Last Message"
        self._attr_native_value = "No messages yet"
        self._attr_extra_state_attributes = {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._ident_nr))},
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
        if data.get("identnr") != self._ident_nr:
            return

        if event_type == "alarm":
            self._attr_native_value = data.get("text", "Unknown Event")
            self._attr_extra_state_attributes = data
            self.async_write_ha_state()
        elif event_type == "status":
             self._attr_native_value = data.get("msg", "Status Message")
             self.async_write_ha_state()


class VdsLastTestMessageSensor(SensorEntity):
    """Sensor showing the timestamp of the last test message."""

    _attr_should_poll = False
    _attr_icon = "mdi:calendar-check"

    def __init__(self, hub, dev_conf):
        self._hub = hub
        self._ident_nr = dev_conf.get("identnr", "Unknown")
        self._attr_unique_id = f"vds_last_test_msg_{self._ident_nr}"
        self._attr_name = f"VdS {self._ident_nr} Last Test Message"
        self._attr_native_value = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._ident_nr))},
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
        if data.get("identnr") != self._ident_nr:
            return

        if event_type == "status" and "Testmeldung" in data.get("msg", ""):
            now = dt_util.now()
            self._attr_native_value = now.strftime("%d.%m.%Y, %H:%M:%S")
            self.async_write_ha_state()


class VdsManufacturerSensor(SensorEntity):
    """Sensor showing the manufacturer ID string from the device."""

    _attr_should_poll = False
    _attr_icon = "mdi:identifier"

    def __init__(self, hub, dev_conf):
        self._hub = hub
        self._ident_nr = dev_conf.get("identnr", "Unknown")
        self._attr_unique_id = f"vds_manufacturer_{self._ident_nr}"
        self._attr_name = f"VdS {self._ident_nr} Manufacturer ID"
        self._attr_native_value = "Unknown"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._ident_nr))},
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
        if data.get("identnr") != self._ident_nr:
            return

        if event_type == "connected":
            ident = data.get("identnr")
            if ident:
                self._attr_native_value = ident
                self.async_write_ha_state()
