import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_PORT

from .const import (
    DOMAIN, 
    DEFAULT_PORT, 
    CONF_DEVICES, 
    CONF_IDENTNR, 
    CONF_KEYNR, 
    CONF_KEY, 
    CONF_ENCRYPT, 
    CONF_VDS_DEVICE, 
    CONF_VDS_AREA, 
    CONF_VDS_OUTPUTS,
    CONF_TEST_INTERVAL,
    CONF_POLLING_INTERVAL, 
    DEFAULT_POLLING_INTERVAL,
    CONF_PERSIST_STATES
)

class VdSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="VdS 2465 Server", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL): int,
                vol.Required(CONF_PERSIST_STATES, default=True): bool
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return VdSOptionsFlowHandler(config_entry)

class VdSOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry_local = config_entry
        self._selected_device_id = None
        super().__init__()

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["global_settings", "add_device", "edit_device", "remove_device"]
        )

    async def async_step_global_settings(self, user_input=None):
        """Step to configure global settings."""
        if user_input is not None:
            new_options = self.config_entry_local.options.copy()
            new_options.update(user_input)
            return self.async_create_entry(title="", data=new_options)

        current_port = self.config_entry_local.data.get(CONF_PORT, DEFAULT_PORT)
        current_interval = self.config_entry_local.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
        current_persist = self.config_entry_local.data.get(CONF_PERSIST_STATES, True)
        
        current_port = self.config_entry_local.options.get(CONF_PORT, current_port)
        current_interval = self.config_entry_local.options.get(CONF_POLLING_INTERVAL, current_interval)
        current_persist = self.config_entry_local.options.get(CONF_PERSIST_STATES, current_persist)

        return self.async_show_form(
            step_id="global_settings",
            data_schema=vol.Schema({
                vol.Required(CONF_PORT, default=current_port): int,
                vol.Required(CONF_POLLING_INTERVAL, default=current_interval): int,
                vol.Required(CONF_PERSIST_STATES, default=current_persist): bool
            })
        )

    async def async_step_add_device(self, user_input=None):
        errors = {}
        if user_input is not None:
            identnr = user_input[CONF_IDENTNR]
            encrypted = user_input.get(CONF_ENCRYPT, True)
            key = user_input.get(CONF_KEY, "")
            
            if encrypted:
                if not user_input.get(CONF_KEYNR) or not key:
                    errors["base"] = "key_required"
                elif len(key) != 32:
                    errors["base"] = "key_length_invalid"
                else:
                    try:
                        int(key, 16)
                    except ValueError:
                        errors["base"] = "key_invalid_hex"
            
            if not errors:
                # Get current options and update devices
                new_options = self.config_entry_local.options.copy()
                devices = new_options.get(CONF_DEVICES, {}).copy()
                
                storage_key = str(identnr)
                devices[storage_key] = {
                    "identnr": identnr,
                    "encrypted": encrypted,
                    "keynr": user_input.get(CONF_KEYNR, 0),
                    "key": key,
                    "stehend": True,
                    "vds_device": user_input.get(CONF_VDS_DEVICE, 1),
                    "vds_area": user_input.get(CONF_VDS_AREA, 1),
                    "vds_outputs": user_input.get(CONF_VDS_OUTPUTS, 0),
                    "test_interval": user_input.get(CONF_TEST_INTERVAL, 0),
                }
                
                new_options[CONF_DEVICES] = devices
                return self.async_create_entry(title="", data=new_options)

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required(CONF_IDENTNR): str,
                vol.Required(CONF_ENCRYPT, default=True): bool,
                vol.Optional(CONF_KEYNR): int,
                vol.Optional(CONF_KEY, default=""): str,
                vol.Optional(CONF_VDS_DEVICE, default=1): int,
                vol.Optional(CONF_VDS_AREA, default=1): int,
                vol.Optional(CONF_VDS_OUTPUTS, default=0): int,
                vol.Optional(CONF_TEST_INTERVAL, default=0): int,
            }),
            errors=errors
        )

    async def async_step_edit_device(self, user_input=None):
        """Selection step for editing a device."""
        devices = self.config_entry_local.options.get(CONF_DEVICES, {})
        if not devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            self._selected_device_id = user_input["device_to_edit"]
            return await self.async_step_edit_device_details()

        # List for dropdown
        options = {k: f"{v['identnr']} (Encrypted: {v.get('encrypted', True)})" for k, v in devices.items()}

        return self.async_show_form(
            step_id="edit_device",
            data_schema=vol.Schema({
                vol.Required("device_to_edit"): vol.In(options)
            })
        )

    async def async_step_edit_device_details(self, user_input=None):
        """Form step for editing device details."""
        errors = {}
        devices = self.config_entry_local.options.get(CONF_DEVICES, {}).copy()
        device_data = devices.get(self._selected_device_id)

        if user_input is not None:
            encrypted = user_input.get(CONF_ENCRYPT, True)
            key = user_input.get(CONF_KEY, "")
            
            if encrypted:
                if not user_input.get(CONF_KEYNR) or not key:
                    errors["base"] = "key_required"
                elif len(key) != 32:
                    errors["base"] = "key_length_invalid"
                else:
                    try:
                        int(key, 16)
                    except ValueError:
                        errors["base"] = "key_invalid_hex"
            
            if not errors:
                # Update existing device entry
                devices[self._selected_device_id].update({
                    "encrypted": encrypted,
                    "keynr": user_input.get(CONF_KEYNR, 0),
                    "key": key,
                    "vds_device": user_input.get(CONF_VDS_DEVICE, 1),
                    "vds_area": user_input.get(CONF_VDS_AREA, 1),
                    "vds_outputs": user_input.get(CONF_VDS_OUTPUTS, 0),
                    "test_interval": user_input.get(CONF_TEST_INTERVAL, 0),
                })
                
                new_options = self.config_entry_local.options.copy()
                new_options[CONF_DEVICES] = devices
                return self.async_create_entry(title="", data=new_options)

        return self.async_show_form(
            step_id="edit_device_details",
            data_schema=vol.Schema({
                vol.Required(CONF_IDENTNR, default=device_data.get("identnr")): str,
                vol.Required(CONF_ENCRYPT, default=device_data.get("encrypted", True)): bool,
                vol.Optional(CONF_KEYNR, default=device_data.get("keynr", 0)): int,
                vol.Optional(CONF_KEY, default=device_data.get("key", "")): str,
                vol.Optional(CONF_VDS_DEVICE, default=device_data.get("vds_device", 1)): int,
                vol.Optional(CONF_VDS_AREA, default=device_data.get("vds_area", 1)): int,
                vol.Optional(CONF_VDS_OUTPUTS, default=device_data.get("vds_outputs", 0)): int,
                vol.Optional(CONF_TEST_INTERVAL, default=device_data.get("test_interval", 0)): int,
            }),
            description_placeholders={"ident": device_data.get("identnr")},
            errors=errors
        )

    async def async_step_remove_device(self, user_input=None):
        if user_input is not None:
            key_to_remove = user_input["device_to_remove"]
            new_options = self.config_entry_local.options.copy()
            devices = new_options.get(CONF_DEVICES, {}).copy()
            
            # 1. Get the identnr of the device to be removed
            removed_device = devices.get(key_to_remove)
            removed_ident = str(removed_device.get("identnr")) if removed_device else None

            # 2. Remove device from devices list
            if key_to_remove in devices:
                del devices[key_to_remove]
            new_options[CONF_DEVICES] = devices

            # 3. Also cleanup discovered_sensors for this identnr
            if removed_ident:
                discovered = new_options.get("discovered_sensors", [])
                new_discovered = [s for s in discovered if str(s.get("ident")) != removed_ident]
                new_options["discovered_sensors"] = new_discovered

            return self.async_create_entry(title="", data=new_options)

        devices = self.config_entry_local.options.get(CONF_DEVICES, {})
        if not devices:
            return self.async_abort(reason="no_devices")

        # Liste für Dropdown erstellen (IdentNr als Label)
        options = {k: f"{v['identnr']} (Encrypted: {v.get('encrypted', True)})" for k, v in devices.items()}

        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required("device_to_remove"): vol.In(options)
            })
        )