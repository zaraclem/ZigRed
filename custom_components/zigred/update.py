"""Explicit Zigbee firmware update via Zigbee2MQTT."""
import json
from homeassistant.components import mqtt
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .firmware import DATA_FIRMWARE


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ReaderFirmware(hass.data[DATA_FIRMWARE], hass.data[DOMAIN][entry.entry_id])])


class ReaderFirmware(CoordinatorEntity, UpdateEntity):
    _attr_has_entity_name = True
    _attr_name = 'Firmware du lecteur'
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, coordinator, hub):
        super().__init__(coordinator)
        self.hub = hub
        self._attr_unique_id = f'{hub.entry.entry_id}_firmware'

    @property
    def device_info(self):
        return {'identifiers': {(DOMAIN, self.hub.entry.entry_id)}, 'name': self.hub.entry.title, 'sw_version': self.hub.firmware_version}

    @property
    def available(self):
        return (super().available and self.hub.paired and self.hub.converter_ready
                and self.hub.ota_capable and self.hub.firmware_version is not None)

    @property
    def installed_version(self):
        return self.hub.firmware_version

    @property
    def latest_version(self):
        return (self.coordinator.data or {}).get('version')

    @property
    def release_url(self):
        return (self.coordinator.data or {}).get('release_url')

    @property
    def in_progress(self):
        return self.hub.update_state in ('updating', 'scheduled')

    @property
    def extra_state_attributes(self):
        return {'progress': self.hub.update_progress, 'error': self.hub.update_error}

    async def async_install(self, version, backup, **kwargs):
        await self.coordinator.async_request_refresh()
        data = self.coordinator.data
        if not self.available or not data or (version and version != data['version']):
            raise HomeAssistantError('Version firmware ou lecteur OTA indisponible')
        if not isinstance(self.hub.file_version, int) or data['file_version'] <= self.hub.file_version:
            raise HomeAssistantError('Le firmware est déjà installé ou plus récent')
        if self.in_progress:
            raise HomeAssistantError('Une mise à jour est déjà en cours')
        # Validate the entire image before instructing Zigbee2MQTT to fetch it.
        await self.coordinator.asset('ota')
        self.hub.update_state = 'scheduled'
        self.hub.update_error = None
        self.hub.changed()
        try:
            await mqtt.async_publish(self.hass, f'{self.hub.base_topic}/bridge/request/device/ota_update/update',
                json.dumps({'id': self.hub.device_id, 'url': data['ota']['url']}), qos=1, retain=False)
        except Exception as error:
            self.hub.update_state = 'idle'
            self.hub.update_error = 'Impossible de transmettre la demande à Zigbee2MQTT'
            self.hub.changed()
            raise HomeAssistantError(self.hub.update_error) from error

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.hub.listeners.add(self.update_from_hub)

    async def async_will_remove_from_hass(self):
        self.hub.listeners.discard(self.update_from_hub)
        await super().async_will_remove_from_hass()

    @callback
    def update_from_hub(self):
        self.async_write_ha_state()
