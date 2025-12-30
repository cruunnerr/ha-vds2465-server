import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_PORT

from .const import DOMAIN, DEFAULT_PORT, CONF_DEVICES, CONF_IDENTNR, CONF_KEYNR, CONF_KEY

class VdSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="VdS 2465 Server", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int
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
        # WICHTIG: FlowHandler __init__ muss aufgerufen werden für internen Status
        super().__init__()

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_device", "remove_device"]
        )

    async def async_step_add_device(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Daten speichern
            devices = self.config_entry_local.options.get(CONF_DEVICES, {}).copy()
            # KeyNr als String Key für JSON Kompatibilität
            key_nr = str(user_input[CONF_KEYNR])
            
            devices[key_nr] = {
                "identnr": user_input[CONF_IDENTNR],
                "keynr": user_input[CONF_KEYNR],
                "key": user_input[CONF_KEY],
                "stehend": True # Default
            }
            
            return self.async_create_entry(title="", data={CONF_DEVICES: devices})

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required(CONF_IDENTNR): str,
                vol.Required(CONF_KEYNR): int,
                vol.Optional(CONF_KEY, default=""): str,
            }),
            errors=errors
        )

    async def async_step_remove_device(self, user_input=None):
        devices = self.config_entry_local.options.get(CONF_DEVICES, {})
        if user_input is not None:
            key_to_remove = user_input["device_to_remove"]
            new_devices = devices.copy()
            if key_to_remove in new_devices:
                del new_devices[key_to_remove]
            return self.async_create_entry(title="", data={CONF_DEVICES: new_devices})

        if not devices:
            return self.async_abort(reason="no_devices")

        # Liste für Dropdown erstellen (IdentNr als Label)
        options = {k: f"{v['identnr']} (KeyNr: {k})" for k, v in devices.items()}

        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required("device_to_remove"): vol.In(options)
            })
        )