"""Device triggers with a live dropdown of this reader's people and UIDs."""
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from homeassistant.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA, InvalidDeviceAutomationConfig,
)
try:
    from homeassistant.components.homeassistant.triggers import event as event_trigger
except ImportError:
    from homeassistant.components.homeassistant import event as event_trigger
from homeassistant.helpers import config_validation as cv, selector

from .automation import EVENT_BADGE, hub_for_device
from .const import DOMAIN

TYPES = ('person_detected', 'person_removed', 'unknown_badge')


def valid_uid(value):
    import re
    value = cv.string(value)
    if value != '*' and not re.fullmatch(r'(?:A:(?:[0-9A-F]{8}|[0-9A-F]{14})|V:[0-9A-F]{16})', value):
        raise vol.Invalid('Select a person UID or *')
    return value


TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({
    vol.Required('domain'): DOMAIN,
    vol.Required('type'): vol.In(TYPES),
    vol.Optional('uid', default='*'): valid_uid,
})


async def async_get_triggers(hass, device_id):
    if hub_for_device(hass, device_id) is None:
        return []
    return [{'platform': 'device', 'domain': DOMAIN, 'device_id': device_id,
             'type': event_type} for event_type in TYPES]


async def async_get_trigger_capabilities(hass, config):
    if config['type'] == 'unknown_badge':
        return {'extra_fields': vol.Schema({})}
    hub = hub_for_device(hass, config['device_id'])
    if hub is None:
        raise InvalidDeviceAutomationConfig('ZigRed reader is not loaded')
    french = hass.config.language.startswith('fr')
    options = [{'value': '*', 'label': 'Toutes les personnes autorisées' if french else 'All enabled people'}]
    for uid, name in sorted(hub.tags.items(), key=lambda item: (item[1].casefold(), item[0])):
        disabled = (' · désactivée' if french else ' · disabled') if not hub.is_enabled(uid) else ''
        options.append({'value': uid, 'label': f'{name} — {uid}{disabled}'})
    saved_uid = config.get('uid', '*')
    if saved_uid != '*' and saved_uid not in hub.tags:
        options.append({'value': saved_uid, 'label': f'{saved_uid} · attribution supprimée' if french else f'{saved_uid} · assignment removed'})
    return {'extra_fields': vol.Schema({
        vol.Required('uid', default=saved_uid): selector.SelectSelector({
            'options': options, 'mode': 'dropdown', 'custom_value': False,
        }),
    })}


async def async_attach_trigger(hass, config, action, trigger_info):
    config = TRIGGER_SCHEMA(config)
    hub = hub_for_device(hass, config['device_id'])
    if hub is None:
        raise InvalidDeviceAutomationConfig('ZigRed reader is not loaded')
    data = {'entry_id': hub.entry.entry_id, 'type': config['type']}
    if config['type'] != 'unknown_badge' and config['uid'] != '*':
        data['uid'] = config['uid']
    event_config = event_trigger.TRIGGER_SCHEMA({
        'platform': 'event', 'event_type': EVENT_BADGE, 'event_data': data,
    })
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type='device')
