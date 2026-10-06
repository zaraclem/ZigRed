"""Select a real paired ZigRed; never create a reader from a guessed topic."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .discovery import discover, valid_base


class ZigRedFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_reconfigure(self, user_input=None):
        self.reconfigure_entry = self._get_reconfigure_entry()
        if self.reconfigure_entry.data.get('kind') == 'workspace':
            return self.async_abort(reason='workspace_no_reconfigure')
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        entry = getattr(self, 'reconfigure_entry', None)
        if not entry and not any(item.data.get('kind') == 'workspace'
                                 for item in self._async_current_entries()):
            return await self.async_step_workspace(user_input)
        default = entry.data.get('base_topic', 'zigbee2mqtt') if entry else 'zigbee2mqtt'
        errors = {}
        if user_input is not None:
            base = user_input['base_topic'].strip().rstrip('/')
            if not valid_base(base):
                errors['base'] = 'invalid_topic'
            else:
                self.base = base
                try:
                    self.devices = await discover(self.hass, base)
                    if self.devices:
                        return await self.async_step_reader()
                    errors['base'] = 'no_readers'
                except (TimeoutError, ValueError, HomeAssistantError):
                    errors['base'] = 'bridge_unavailable'
            default = base
        return self.async_show_form(step_id='user', data_schema=vol.Schema({
            vol.Required('base_topic', default=default): str}), errors=errors)

    async def async_step_workspace(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id('zigred_workspace')
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title='Espace ZigRed', data={'kind': 'workspace'})
        return self.async_show_form(step_id='workspace', data_schema=vol.Schema({}))

    async def async_step_reader(self, user_input=None):
        errors = {}
        if user_input is not None:
            address = user_input['reader']
            try:
                # Recheck after selection so a removed device cannot be registered.
                devices = await discover(self.hass, self.base)
            except (TimeoutError, ValueError, HomeAssistantError):
                return self.async_abort(reason='bridge_unavailable')
            device = devices.get(address)
            if device is None:
                return self.async_abort(reason='reader_removed')
            topic = f"{self.base}/{device['friendly_name']}"
            data = {'topic': topic, 'base_topic': self.base,
                    'device_id': device['friendly_name'], 'ieee_address': address}
            current = getattr(self, 'reconfigure_entry', None)
            for entry in self._async_current_entries():
                if current and entry.entry_id == current.entry_id:
                    continue
                if (entry.unique_id == address or entry.data.get('ieee_address') == address
                        or entry.data.get('topic') == topic):
                    if not current and not entry.data.get('ieee_address'):
                        # Bind an existing manual entry without losing names or UIDs.
                        self.hass.config_entries.async_update_entry(entry, unique_id=address, data=data)
                        await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason='already_configured')
            await self.async_set_unique_id(address)
            if current:
                self.hass.config_entries.async_update_entry(current, unique_id=address, data=data)
                await self.hass.config_entries.async_reload(current.entry_id)
                return self.async_abort(reason='reconfigure_successful')
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"ZigRed · {device['friendly_name']}", data=data)
        choices = {address: f"{device['friendly_name']} — {device['model']} — {address}"
                   for address, device in self.devices.items()}
        return self.async_show_form(step_id='reader', data_schema=vol.Schema({
            vol.Required('reader'): vol.In(choices)}), errors=errors)
