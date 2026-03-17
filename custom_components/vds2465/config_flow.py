import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_PORT

from .const import (
    DOMAIN, 
    CONF_KEYS,
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
        self._selected_key_id = None
        super().__init__()

    def _get_key_options_with_usage(self):
        """Helper to get key numbers with their usage information."""
        keys = self.config_entry_local.options.get(CONF_KEYS, {})
        devices = self.config_entry_local.options.get(CONF_DEVICES, {})
        
        # Map keynr -> identnr
        key_usage = {}
        for dev in devices.values():
            kn = str(dev.get("keynr", ""))
            if kn and kn != "0":
                key_usage[kn] = dev.get("identnr")
        
        key_options = {"0": "Kein Schlüssel"}
        # Sort keys numerically
        sorted_keys = sorted(keys.keys(), key=lambda x: int(x) if x.isdigit() else x)
        for k in sorted_keys:
            label = f"{k}"
            if k in key_usage:
                label += f" (verwendet von {key_usage[k]})"
            key_options[k] = label
        return key_options

    async def async_step_init(self, user_input=None):
        # Migration: Ensure CONF_KEYS exists in options
        if CONF_KEYS not in self.config_entry_local.options:
            new_options = self.config_entry_local.options.copy()
            keys = {}
            devices = new_options.get(CONF_DEVICES, {})
            for dev_data in devices.values():
                if dev_data.get("encrypted", True) and dev_data.get("keynr"):
                    keys[str(dev_data.get("keynr"))] = dev_data.get("key", "")
            new_options[CONF_KEYS] = keys
            self.hass.config_entries.async_update_entry(self.config_entry_local, options=new_options)

        return self.async_show_menu(
            step_id="init",
            menu_options=["global_settings", "manage_keys", "manage_devices"]
        )

    async def async_step_manage_devices(self, user_input=None):
        """Step to manage devices."""
        return self.async_show_menu(
            step_id="manage_devices",
            menu_options=["add_device", "edit_device_select", "remove_device", "back"]
        )

    async def async_step_manage_keys(self, user_input=None):
        """Step to manage keys menu."""
        return self.async_show_menu(
            step_id="manage_keys",
            menu_options=["add_key", "edit_key_select", "back"]
        )

    async def async_step_back(self, user_input=None):
        """Go back to main menu."""
        return await self.async_step_init()

    async def async_step_add_key(self, user_input=None):
        """Step to add a new key."""
        errors = {}
        if user_input is not None:
            keynr = str(user_input[CONF_KEYNR])
            key = user_input[CONF_KEY]
            
            keys = self.config_entry_local.options.get(CONF_KEYS, {}).copy()
            
            if keynr in keys:
                errors["base"] = "key_nr_already_exists"
            elif len(key) != 32:
                errors["base"] = "key_length_invalid"
            else:
                try:
                    int(key, 16)
                except ValueError:
                    errors["base"] = "key_invalid_hex"
            
            if not errors:
                keys[keynr] = key
                new_options = self.config_entry_local.options.copy()
                new_options[CONF_KEYS] = keys
                return self.async_create_entry(title="", data=new_options)

        return self.async_show_form(
            step_id="add_key",
            data_schema=vol.Schema({
                vol.Required(CONF_KEYNR): int,
                vol.Required(CONF_KEY): str,
            }),
            errors=errors
        )

    async def async_step_edit_key_select(self, user_input=None):
        """Step to select a key for editing."""
        key_options = self._get_key_options_with_usage()
        if not key_options:
            return self.async_abort(reason="no_keys")

        if user_input is not None:
            self._selected_key_id = user_input["key_to_edit"]
            return await self.async_step_edit_key_details()

        return self.async_show_form(
            step_id="edit_key_select",
            data_schema=vol.Schema({
                vol.Required("key_to_edit"): vol.In(key_options)
            })
        )

    async def async_step_edit_key_details(self, user_input=None):
        """Step to edit key details or delete the key."""
        errors = {}
        keys = self.config_entry_local.options.get(CONF_KEYS, {}).copy()
        current_key = keys.get(self._selected_key_id, "")

        if user_input is not None:
            if user_input.get("delete_key"):
                if self._selected_key_id in keys:
                    del keys[self._selected_key_id]
                new_options = self.config_entry_local.options.copy()
                new_options[CONF_KEYS] = keys
                return self.async_create_entry(title="", data=new_options)
            
            key = user_input[CONF_KEY]
            if len(key) != 32:
                errors["base"] = "key_length_invalid"
            else:
                try:
                    int(key, 16)
                except ValueError:
                    errors["base"] = "key_invalid_hex"
            
            if not errors:
                keys[self._selected_key_id] = key
                new_options = self.config_entry_local.options.copy()
                new_options[CONF_KEYS] = keys
                return self.async_create_entry(title="", data=new_options)

        return self.async_show_form(
            step_id="edit_key_details",
            data_schema=vol.Schema({
                vol.Required(CONF_KEY, default=current_key): str,
                vol.Optional("delete_key", default=False): bool,
            }),
            description_placeholders={"keynr": self._selected_key_id},
            errors=errors
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
        keys = self.config_entry_local.options.get(CONF_KEYS, {})
        
        if user_input is not None:
            identnr = user_input[CONF_IDENTNR]
            encrypted = user_input.get(CONF_ENCRYPT, True)
            keynr = user_input.get(CONF_KEYNR, "0")
            
            existing_devices = self.config_entry_local.options.get(CONF_DEVICES, {})
            
            # Check for duplicate identnr
            if str(identnr) in existing_devices:
                errors["base"] = "ident_already_exists"
            
            if not errors and encrypted:
                if not keynr or str(keynr) == "0":
                    errors["base"] = "key_required"
                
                # Check for duplicate keynr in devices (ignoring "0")
                if not errors and str(keynr) != "0":
                    for dev_data in existing_devices.values():
                        if dev_data.get("encrypted", True) and str(dev_data.get("keynr")) == str(keynr):
                            errors["base"] = "key_nr_already_in_use"
                            break
            
            if not errors:
                new_options = self.config_entry_local.options.copy()
                devices = existing_devices.copy()
                
                # Force clean values if not encrypted
                final_keynr = int(keynr) if encrypted else 0
                final_key = keys.get(str(keynr), "") if encrypted and str(keynr) != "0" else ""

                storage_key = str(identnr)
                devices[storage_key] = {
                    "identnr": identnr,
                    "encrypted": encrypted,
                    "keynr": final_keynr,
                    "key": final_key,
                    "stehend": True,
                    "vds_device": user_input.get(CONF_VDS_DEVICE, 1),
                    "vds_area": user_input.get(CONF_VDS_AREA, 1),
                    "vds_outputs": user_input.get(CONF_VDS_OUTPUTS, 0),
                    "test_interval": user_input.get(CONF_TEST_INTERVAL, 0),
                }
                
                new_options[CONF_DEVICES] = devices
                return self.async_create_entry(title="", data=new_options)

        key_options = self._get_key_options_with_usage()
        
        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required(CONF_IDENTNR): str,
                vol.Required(CONF_ENCRYPT, default=True): bool,
                vol.Optional(CONF_KEYNR, default="0"): vol.In(key_options),
                vol.Optional(CONF_VDS_DEVICE, default=1): int,
                vol.Optional(CONF_VDS_AREA, default=1): int,
                vol.Optional(CONF_VDS_OUTPUTS, default=0): int,
                vol.Optional(CONF_TEST_INTERVAL, default=0): int,
            }),
            errors=errors
        )

    async def async_step_edit_device_select(self, user_input=None):
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
            step_id="edit_device_select",
            data_schema=vol.Schema({
                vol.Required("device_to_edit"): vol.In(options)
            })
        )

    async def async_step_edit_device_details(self, user_input=None):
        """Form step for editing device details."""
        errors = {}
        devices = self.config_entry_local.options.get(CONF_DEVICES, {}).copy()
        device_data = devices.get(self._selected_device_id)
        keys = self.config_entry_local.options.get(CONF_KEYS, {})

        if user_input is not None:
            encrypted = user_input.get(CONF_ENCRYPT, True)
            keynr = user_input.get(CONF_KEYNR, "0")
            
            if encrypted:
                if not keynr or str(keynr) == "0":
                    errors["base"] = "key_required"
                
                # Check for duplicate keynr (ignoring "0")
                if not errors and str(keynr) != "0":
                    for dev_id, dev_data in devices.items():
                        if dev_id == self._selected_device_id:
                            continue
                        if dev_data.get("encrypted", True) and str(dev_data.get("keynr")) == str(keynr):
                            errors["base"] = "key_nr_already_in_use"
                            break
            
            if not errors:
                # Force clean values if not encrypted
                final_keynr = int(keynr) if encrypted else 0
                final_key = keys.get(str(keynr), "") if encrypted and str(keynr) != "0" else ""

                # Update existing device entry
                devices[self._selected_device_id].update({
                    "encrypted": encrypted,
                    "keynr": final_keynr,
                    "key": final_key,
                    "vds_device": user_input.get(CONF_VDS_DEVICE, 1),
                    "vds_area": user_input.get(CONF_VDS_AREA, 1),
                    "vds_outputs": user_input.get(CONF_VDS_OUTPUTS, 0),
                    "test_interval": user_input.get(CONF_TEST_INTERVAL, 0),
                })
                
                new_options = self.config_entry_local.options.copy()
                new_options[CONF_DEVICES] = devices
                return self.async_create_entry(title="", data=new_options)

        key_options = self._get_key_options_with_usage()
        current_keynr = str(device_data.get("keynr", "0"))

        return self.async_show_form(
            step_id="edit_device_details",
            data_schema=vol.Schema({
                vol.Required(CONF_IDENTNR, default=device_data.get("identnr")): str,
                vol.Required(CONF_ENCRYPT, default=device_data.get("encrypted", True)): bool,
                vol.Optional(CONF_KEYNR, default=current_keynr): vol.In(key_options),
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