import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_DEVICES, CONF_PERSIST_STATES

_LOGGER = logging.getLogger(__name__)

# Persistent device-level attributes
VDS_PERSISTENT_ATTRIBUTES = [
    "identnr"
]

# Message-specific attributes that should reset to '-' if not in current message
VDS_MESSAGE_ATTRIBUTES = [
    "text",
    "geraet",
    "bereich",
    "adresse",
    "code",
    "type",
    "zustand",
    "quelle",
    "entstehungszeit",
    "priority",
    "transport_service",
    "telegram_counter",
    "area_name",
    "manufacturer",
    "msg_text"
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VdS sensors."""
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = entry.options.get(CONF_DEVICES, {})
    persist = entry.options.get(CONF_PERSIST_STATES, entry.data.get(CONF_PERSIST_STATES, True))

    entities = []
    for dev_conf in devices.values():
        entities.append(VdsLastMessageSensor(hub, dev_conf, persist))
        entities.append(VdsLastTestMessageSensor(hub, dev_conf, persist))
        entities.append(VdsManufacturerSensor(hub, dev_conf, persist))

    async_add_entities(entities)

    # Init Sensor Manager for dynamic address sensors
    manager = VdsSensorManager(hass, hub, entry, async_add_entities, persist)
    
    # ALWAYS restore dynamically discovered sensors entities from options
    # This ensures sensors don't disappear if persistence is disabled.
    await manager.restore_discovered_sensors()
        
    entry.async_on_unload(manager.unload)


class VdsSensorManager:
    """Manages dynamic creation of sensors for VdS addresses."""
    
    def __init__(self, hass, hub, entry, async_add_entities, persist):
        self.hass = hass
        self.hub = hub
        self.entry = entry
        self.async_add_entities = async_add_entities
        self.persist = persist
        self.known_sensors = set() # (identnr, adresse, type_prefix) tuples
        self._remove_listener = self.hub.add_listener(self._handle_event)

    def unload(self):
        """Unload the manager and remove listener."""
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None

    async def restore_discovered_sensors(self):
        """Re-create previously discovered sensors from storage."""
        discovered = self.entry.options.get("discovered_sensors", [])
        if not discovered:
            return
            
        entities = []
        for s in discovered:
            identnr = s["ident"]
            adresse = s["addr"]
            prefix = s["type"]
            key = (str(identnr), str(adresse), prefix)
            
            if key not in self.known_sensors:
                self.known_sensors.add(key)
                if prefix == "out":
                    entities.append(VdsOutputSensor(self.hub, identnr, adresse, self.persist))
                else:
                    entities.append(VdsAddressSensor(self.hub, identnr, adresse, self.persist))
        
        if entities:
            _LOGGER.debug(f"Restoring {len(entities)} discovered VdS sensors")
            self.async_add_entities(entities)

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
                sensor = VdsOutputSensor(self.hub, identnr, adresse, self.persist)
            else:
                _LOGGER.info(f"Discovered new VdS address: {identnr} / {adresse}")
                sensor = VdsAddressSensor(self.hub, identnr, adresse, self.persist)
                
            self.async_add_entities([sensor])
            
            # ALWAYS save discovered sensors to options so they persist across restarts
            discovered = self.entry.options.get("discovered_sensors", []).copy()
            # Avoid duplicates
            if not any(d["ident"] == str(identnr) and d["addr"] == int(adresse) and d["type"] == type_prefix for d in discovered):
                discovered.append({"ident": str(identnr), "addr": int(adresse), "type": type_prefix})
                
                # Update options without triggering a full reload
                new_options = self.entry.options.copy()
                new_options["discovered_sensors"] = discovered
                self.hass.config_entries.async_update_entry(self.entry, options=new_options)


class VdsAddressSensor(RestoreEntity, SensorEntity):
    """Sensor representing a specific VdS Address (Zone)."""

    _attr_should_poll = False
    _attr_icon = "mdi:shield-home"

    def __init__(self, hub, identnr, adresse, persist):
        self._hub = hub
        self._ident_nr = str(identnr)
        self._adresse = int(adresse)
        self._persist = persist
        
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
        """Register callbacks and restore state."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))
        
        if self._persist:
            last_state = await self.async_get_last_state()
            if last_state:
                self._attr_native_value = last_state.state
                self._attr_extra_state_attributes.update(last_state.attributes)

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        if str(data.get("identnr")) != self._ident_nr:
            return
        
        if event_type == "alarm":
            if data.get("quelle") == "Ausgang":
                return

            msg_addr = data.get("adresse")
            if msg_addr is not None and int(msg_addr) == self._adresse:
                self._attr_native_value = data.get("text", "Unknown Event")
                self._attr_extra_state_attributes = data.copy()
                
                if "msg_text" in data:
                    self._attr_extra_state_attributes["message_text"] = data["msg_text"]
                    
                self.async_write_ha_state()


class VdsOutputSensor(RestoreEntity, SensorEntity):
    """Sensor representing the feedback state of a VdS Output."""

    _attr_should_poll = False
    _attr_icon = "mdi:toggle-switch"

    def __init__(self, hub, identnr, adresse, persist):
        self._hub = hub
        self._ident_nr = str(identnr)
        self._adresse = int(adresse)
        self._persist = persist
        
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
        """Register callbacks and restore state."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))
        
        if self._persist:
            last_state = await self.async_get_last_state()
            if last_state:
                self._attr_native_value = last_state.state
                self._attr_extra_state_attributes.update(last_state.attributes)

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        if str(data.get("identnr")) != self._ident_nr:
            return
        
        if event_type == "alarm":
            if data.get("quelle") != "Ausgang":
                return

            msg_addr = data.get("adresse")
            if msg_addr is not None and int(msg_addr) == self._adresse:
                self._attr_native_value = data.get("zustand", data.get("text", "Unknown"))
                self._attr_extra_state_attributes = data.copy()
                self.async_write_ha_state()


class VdsLastMessageSensor(RestoreEntity, SensorEntity):
    """Sensor showing the last message from a VdS device."""

    _attr_should_poll = False
    _attr_icon = "mdi:message-text-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, dev_conf, persist):
        self._hub = hub
        self._ident_nr = str(dev_conf.get("identnr", "Unknown"))
        self._persist = persist
        self._attr_unique_id = f"vds_last_msg_{self._ident_nr}"
        self._attr_name = f"VdS {self._ident_nr} Last Message"
        self._attr_native_value = "No messages yet"
        
        # Initial attributes with placeholders
        self._attr_extra_state_attributes = {key: "-" for key in VDS_PERSISTENT_ATTRIBUTES + VDS_MESSAGE_ATTRIBUTES}
        self._attr_extra_state_attributes["identnr"] = self._ident_nr
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._ident_nr))},
            "name": f"VdS Device {self._ident_nr}",
            "manufacturer": "VdS 2465",
            "model": "Generic ID",
        }

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))
        
        if self._persist:
            last_state = await self.async_get_last_state()
            if last_state:
                self._attr_native_value = last_state.state
                self._attr_extra_state_attributes.update(last_state.attributes)

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        if str(data.get("identnr")) != str(self._ident_nr):
            return
        
        if event_type in ["alarm", "status"]:
            for key in VDS_MESSAGE_ATTRIBUTES:
                self._attr_extra_state_attributes[key] = "-"
            
            self._attr_extra_state_attributes.update(data)
            
            if event_type == "alarm":
                self._attr_native_value = data.get("text", "Unknown Event")
            else:
                self._attr_native_value = data.get("msg", "Status Message")
            
            if "msg_text" in data:
                self._attr_extra_state_attributes["message_text"] = data["msg_text"]

            self.async_write_ha_state()

        elif event_type in ["area_update", "manufacturer_update", "features_update"]:
            if event_type == "features_update":
                self._attr_extra_state_attributes.update(data.get("features", {}))
            else:
                self._attr_extra_state_attributes.update(data)
            
            self.async_write_ha_state()


class VdsLastTestMessageSensor(RestoreEntity, SensorEntity):
    """Sensor showing the timestamp of the last test message."""

    _attr_should_poll = False
    _attr_icon = "mdi:calendar-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, dev_conf, persist):
        self._hub = hub
        self._ident_nr = dev_conf.get("identnr", "Unknown")
        self._persist = persist
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
        """Register callbacks and restore state."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))
        
        if self._persist:
            last_state = await self.async_get_last_state()
            if last_state:
                self._attr_native_value = last_state.state

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        if str(data.get("identnr")) != str(self._ident_nr):
            return

        if event_type == "status" and "Testmeldung" in data.get("msg", ""):
            now = dt_util.now()
            self._attr_native_value = now.strftime("%d.%m.%Y, %H:%M:%S")
            self.async_write_ha_state()


class VdsManufacturerSensor(RestoreEntity, SensorEntity):
    """Sensor showing the manufacturer ID string from the device."""

    _attr_should_poll = False
    _attr_icon = "mdi:identifier"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, dev_conf, persist):
        self._hub = hub
        self._ident_nr = dev_conf.get("identnr", "Unknown")
        self._persist = persist
        self._attr_unique_id = f"vds_manufacturer_{self._ident_nr}"
        self._attr_name = f"VdS {self._ident_nr} Manufacturer ID"
        self._attr_native_value = "Unknown"
        self._attr_extra_state_attributes = {}
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._ident_nr))},
            "name": f"VdS Device {self._ident_nr}",
            "manufacturer": "VdS 2465",
            "model": "Generic ID",
        }

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))
        
        if self._persist:
            last_state = await self.async_get_last_state()
            if last_state:
                self._attr_native_value = last_state.state
                self._attr_extra_state_attributes.update(last_state.attributes)

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        if str(data.get("identnr")) != str(self._ident_nr):
            return

        if event_type == "connected":
            ident = data.get("identnr")
            if ident:
                if self._attr_native_value == "Unknown": 
                     self._attr_native_value = ident
                     self.async_write_ha_state()
        
        elif event_type == "manufacturer_update":
            manufacturer = data.get("manufacturer")
            if manufacturer:
                self._attr_native_value = manufacturer
                self.async_write_ha_state()

        elif event_type == "features_update":
            features = data.get("features")
            if features:
                self._attr_extra_state_attributes.update(features)
                self.async_write_ha_state()
