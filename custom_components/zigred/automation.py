"""Reader-scoped automation events; names are labels and UIDs are stable keys."""
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

EVENT_BADGE = 'zigred_badge'


def hub_for_device(hass, device_id):
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for domain, entry_id in device.identifiers:
        if domain == DOMAIN:
            return hass.data.get(DOMAIN, {}).get(entry_id)
    return None


def fire_badge_event(hub, event_type, uid, person=None):
    device = dr.async_get(hub.hass).async_get_device(
        identifiers={(DOMAIN, hub.entry.entry_id)})
    hub.hass.bus.async_fire(EVENT_BADGE, {
        'type': event_type, 'entry_id': hub.entry.entry_id,
        'device_id': device.id if device else None,
        'reader': hub.entry.title, 'ieee_address': hub.ieee_address,
        'uid': uid, 'person': person,
    })
