from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BadgePresentEntity(hub)])


class BadgePresentEntity(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = 'Lecture en cours'
    _attr_icon = 'mdi:nfc-variant'

    def __init__(self, hub):
        self.hub = hub
        self._attr_unique_id = f'{hub.entry.entry_id}_badge_present'

    @property
    def device_info(self):
        return {'identifiers': {(DOMAIN, self.hub.entry.entry_id)}, 'name': self.hub.entry.title}

    @property
    def is_on(self):
        return self.hub.current_uid is not None

    @property
    def available(self):
        return self.hub.paired and self.hub.converter_ready

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.hub.listeners.add(self.update_from_hub)

    async def async_will_remove_from_hass(self):
        self.hub.listeners.discard(self.update_from_hub)
        await super().async_will_remove_from_hass()

    @callback
    def update_from_hub(self):
        self.async_write_ha_state()
