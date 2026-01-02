from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, CONF_DEVICES

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VdS switches."""
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = entry.options.get(CONF_DEVICES, {})

    entities = []
    for dev_conf in devices.values():
        identnr = dev_conf.get("identnr", "Unknown")
        # Create 40 outputs per device
        for i in range(1, 41):
            entities.append(VdsOutputSwitch(hub, identnr, i))

    async_add_entities(entities)


class VdsOutputSwitch(SwitchEntity):
    """Switch representing a VdS output."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_should_poll = False
    # Default to disabled so user can enable what they need
    _attr_entity_registry_enabled_default = False 

    def __init__(self, hub, identnr, address):
        self._hub = hub
        self._ident_nr = identnr
        self._address = address
        
        # Default to Device 1, Area 1 if unknown. 
        # Will be updated if we receive a status packet for this output.
        self._device = 1
        self._area = 1
        
        self._attr_unique_id = f"vds_output_{self._ident_nr}_{self._address}"
        self._attr_name = f"VdS {self._ident_nr} Output {self._address}"
        self._attr_is_on = None # Unknown state initially
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self._ident_nr))},
            "name": f"VdS Device {self._ident_nr}",
            "manufacturer": "VdS 2465",
            "model": "Generic ID",
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(self._hub.add_listener(self._handle_event))

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._hub.send_output(self._ident_nr, self._address, True, device=self._device, area=self._area)
        # Optimistically set state, but it will be confirmed by event if VdS acknowledges
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._hub.send_output(self._ident_nr, self._address, False, device=self._device, area=self._area)
        # Optimistically set state
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_event(self, event_type, data):
        """Handle events from VdS Hub."""
        if data.get("identnr") != self._ident_nr:
            return

        # Check for Output status update
        # We look for "alarm" events where source is "Ausgang" and address matches
        if event_type == "alarm":
            if data.get("quelle") == "Ausgang" and data.get("adresse") == self._address:
                # Update learned Device/Area
                if "geraet" in data:
                    self._device = data["geraet"]
                if "bereich" in data:
                    self._area = data["bereich"]

                zustand = data.get("zustand")
                if zustand == "Ein":
                    self._attr_is_on = True
                elif zustand == "Aus":
                    self._attr_is_on = False
                self.async_write_ha_state()
