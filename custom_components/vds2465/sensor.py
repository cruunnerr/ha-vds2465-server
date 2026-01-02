import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_DEVICES

_LOGGER = logging.getLogger(__name__)

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

    # Init Sensor Manager for dynamic address sensors
    manager = VdsSensorManager(hass, hub, async_add_entities)
    entry.async_on_unload(manager.unload)


class VdsSensorManager:
    """Manages dynamic creation of sensors for VdS addresses."""
    
    def __init__(self, hass, hub, async_add_entities):
        self.hass = hass
        self.hub = hub
        self.async_add_entities = async_add_entities
        self.known_sensors = set() # (identnr, adresse) tuples
        self._remove_listener = self.hub.add_listener(self._handle_event)

    def unload(self):
        """Unload the manager and remove listener."""
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None

    def _handle_event(self, event_type, data):
        """Listen for alarms to discover new addresses."""
        if event_type != "alarm":
            return

        identnr = data.get("identnr")
        adresse = data.get("adresse")
        quelle = data.get("quelle")
        
        if identnr is None or adresse is None:
            return
            
        # Determine sensor type based on source
        is_output = (quelle == "Ausgang")
        
        # Use different key prefix for map to distinguish address vs output sensors for same address ID
        type_prefix = "out" if is_output else "addr"
        key = (str(identnr), str(adresse), type_prefix)
        
        if key not in self.known_sensors:
            self.known_sensors.add(key)
            
            if is_output:
                _LOGGER.info(f"Discovered new VdS output feedback: {identnr} / {adresse}")
                sensor = VdsOutputSensor(self.hub, identnr, adresse)
            else:
                _LOGGER.info(f"Discovered new VdS address: {identnr} / {adresse}")
                sensor = VdsAddressSensor(self.hub, identnr, adresse)
                
            self.async_add_entities([sensor])


class VdsAddressSensor(SensorEntity):
    """Sensor representing a specific VdS Address (Zone)."""

    _attr_should_poll = False
    _attr_icon = "mdi:shield-home"

    def __init__(self, hub, identnr, adresse):
        self._hub = hub
        self._ident_nr = str(identnr)
        self._adresse = int(adresse) # keep as int for comparison if needed, or str
        
        # Unique ID combining IdentNr and Address
        self._attr_unique_id = f"vds_{self._ident_nr}_addr_{self._adresse}"
        self._attr_name = f"VdS {self._ident_nr} Address {self._adresse}"
        self._attr_native_value = "Unknown"
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
        # Filter for this specific device
        if str(data.get("identnr")) != self._ident_nr:
            return
        
        # We only update specific address sensors if an alarm for this address occurs
        if event_type == "alarm":
            # Ensure we only track non-output events (inputs/zones)
            if data.get("quelle") == "Ausgang":
                return

            msg_addr = data.get("adresse")
            if msg_addr is not None and int(msg_addr) == self._adresse:
                self._attr_native_value = data.get("text", "Unknown Event")
                
                # Update attributes with all available data (includes aligned area_name from lib)
                self._attr_extra_state_attributes.update(data)
                
                # Add specific message text if available in payload
                if "msg_text" in data:
                    self._attr_extra_state_attributes["message_text"] = data["msg_text"]
                    
                self.async_write_ha_state()


class VdsOutputSensor(SensorEntity):
    """Sensor representing the feedback state of a VdS Output."""

    _attr_should_poll = False
    _attr_icon = "mdi:toggle-switch"

    def __init__(self, hub, identnr, adresse):
        self._hub = hub
        self._ident_nr = str(identnr)
        self._adresse = int(adresse)
        
        # Unique ID for Output Sensor
        self._attr_unique_id = f"vds_{self._ident_nr}_output_{self._adresse}"
        self._attr_name = f"VdS {self._ident_nr} Output {self._adresse}"
        self._attr_native_value = "Unknown"
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
        if str(data.get("identnr")) != self._ident_nr:
            return
        
        if event_type == "alarm":
            # Ensure we only track output events
            if data.get("quelle") != "Ausgang":
                return

            msg_addr = data.get("adresse")
            if msg_addr is not None and int(msg_addr) == self._adresse:
                # For outputs, typically we get "Ein" or "Aus" in "zustand"
                # But we can also show the text
                self._attr_native_value = data.get("zustand", data.get("text", "Unknown"))
                
                self._attr_extra_state_attributes.update(data)
                self.async_write_ha_state()


class VdsLastMessageSensor(SensorEntity):
    """Sensor showing the last message from a VdS device."""

    _attr_should_poll = False
    _attr_icon = "mdi:message-text-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, dev_conf):
        self._hub = hub
        self._ident_nr = str(dev_conf.get("identnr", "Unknown"))
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
        if str(data.get("identnr")) != str(self._ident_nr):
            return
        
        if event_type == "area_update":
            self._attr_extra_state_attributes["area_name"] = data.get("area_name")
            self.async_write_ha_state()

        elif event_type == "alarm":
            self._attr_native_value = data.get("text", "Unknown Event")
            self._attr_extra_state_attributes.update(data)
            
            if "msg_text" in data:
                self._attr_extra_state_attributes["message_text"] = data["msg_text"]

            self.async_write_ha_state()
        elif event_type == "status":
             self._attr_native_value = data.get("msg", "Status Message")
             self._attr_extra_state_attributes.update(data)
             self.async_write_ha_state()


class VdsLastTestMessageSensor(SensorEntity):
    """Sensor showing the timestamp of the last test message."""

    _attr_should_poll = False
    _attr_icon = "mdi:calendar-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
        if str(data.get("identnr")) != str(self._ident_nr):
            return

        if event_type == "status" and "Testmeldung" in data.get("msg", ""):
            now = dt_util.now()
            self._attr_native_value = now.strftime("%d.%m.%Y, %H:%M:%S")
            self.async_write_ha_state()


class VdsManufacturerSensor(SensorEntity):
    """Sensor showing the manufacturer ID string from the device."""

    _attr_should_poll = False
    _attr_icon = "mdi:identifier"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
        if str(data.get("identnr")) != str(self._ident_nr):
            return

        if event_type == "connected":
            ident = data.get("identnr")
            if ident:
                # We prioritize the full manufacturer string if available, otherwise ident
                if self._attr_native_value == "Unknown": 
                     self._attr_native_value = ident
                     self.async_write_ha_state()
        
        elif event_type == "manufacturer_update":
            manufacturer = data.get("manufacturer")
            if manufacturer:
                self._attr_native_value = manufacturer
                self.async_write_ha_state()
