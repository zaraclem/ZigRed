from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        CurrentPersonSensor(hub), CurrentBadgeSensor(hub),
    ])


class ReaderSensor(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, hub, suffix):
        self.hub = hub
        self._attr_unique_id = f'{hub.entry.entry_id}_{suffix}'

    @property
    def device_info(self):
        return {'identifiers': {(DOMAIN, self.hub.entry.entry_id)}, 'name': self.hub.entry.title}

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


class CurrentPersonSensor(ReaderSensor):
    _attr_name = 'Personne active'
    _attr_icon = 'mdi:account'

    def __init__(self, hub):
        super().__init__(hub, 'current_person')

    @property
    def native_value(self):
        uid = self.hub.current_uid
        if uid is None:
            return 'Aucun'
        return self.hub.tags.get(uid, 'Badge inconnu')


class CurrentBadgeSensor(ReaderSensor):
    _attr_name = 'UID actif'
    _attr_icon = 'mdi:nfc'

    def __init__(self, hub):
        super().__init__(hub, 'current_badge')

    @property
    def native_value(self):
        return self.hub.current_uid or 'Aucun'
