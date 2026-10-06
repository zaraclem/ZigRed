"""Admin-only, reader-scoped person management for the sidebar panel."""
from time import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import device_registry as dr

from . import UID_RE
from .const import DOMAIN
from .firmware import require_admin
from .led import validate_settings, encode_settings


def reader_data(hub):
    uid = hub.current_uid
    return {
        'entry_id': hub.entry.entry_id, 'name': hub.entry.title,
        'topic': hub.entry.data['topic'], 'device_id': hub.device_id,
        'ieee_address': hub.ieee_address, 'paired': hub.paired,
        'converter_ready': hub.converter_ready,
        'current_uid': uid, 'current_person': hub.tags.get(uid, 'Badge inconnu') if uid else None,
        'present': uid is not None, 'scanned_uid': next(reversed(hub.active), None),
        'enrolling': hub.enrolling, 'pending_name': hub.pending_name,
        'firmware_version': hub.firmware_version,
        'led': hub.led_settings, 'led_capable': hub.led_capable,
        'led_synced': hub.led_applied == encode_settings(hub.led_settings),
        'led_error': hub.led_error,
        'people': [{'uid': badge, 'name': name, 'enabled': hub.is_enabled(badge),
                    'disabled_until': hub.disabled.get(badge),
                    'present': badge in hub.active and hub.is_enabled(badge)}
                   for badge, name in hub.tags.items()],
    }


class ReadersView(HomeAssistantView):
    url = '/api/zigred/readers'
    name = 'api:zigred:readers'
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        require_admin(request)
        return self.json({'readers': [reader_data(hub)
                         for hub in self.hass.data.get(DOMAIN, {}).values()]})

    async def post(self, request):
        require_admin(request)
        try:
            payload = await request.json()
        except (ValueError, TypeError) as error:
            raise web.HTTPBadRequest(text='Demande invalide.') from error
        if not isinstance(payload, dict) or not isinstance(payload.get('entry_id'), str):
            raise web.HTTPBadRequest(text='Choisis un lecteur.')
        hub = self.hass.data.get(DOMAIN, {}).get(payload['entry_id'])
        if hub is None:
            raise web.HTTPNotFound(text='Lecteur non configuré ou indisponible.')
        action = payload.get('action')
        if not hub.paired and action != 'rename_reader':
            raise web.HTTPConflict(text='Associe d’abord cette configuration à un lecteur appairé dans Zigbee2MQTT.')
        name = payload.get('name')
        if action in ('upsert', 'enroll', 'rename_reader'):
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
                raise web.HTTPBadRequest(text='Le nom doit contenir entre 1 et 80 caractères.')
            name = name.strip()
        if action in ('upsert', 'remove', 'toggle'):
            uid = payload.get('uid')
            if not isinstance(uid, str) or not UID_RE.fullmatch(uid.strip().upper()):
                raise web.HTTPBadRequest(text='UID attendu : A: puis 8 ou 14 caractères hexadécimaux, ou V: puis 16.')
            uid = uid.strip().upper()
            if action != 'upsert' and uid not in hub.tags:
                raise web.HTTPNotFound(text='Cette personne n’existe plus sur ce lecteur.')
        if action == 'led':
            try:
                hub.led_settings = validate_settings(payload.get('settings'))
            except ValueError as error:
                raise web.HTTPBadRequest(text=str(error)) from error
            hub.save()
            await hub.sync_led(force=True)
            hub.changed()
        elif action == 'upsert':
            previous = payload.get('previous_uid')
            if previous is not None and (not isinstance(previous, str) or previous not in hub.tags):
                raise web.HTTPNotFound(text='La personne à modifier n’existe plus sur ce lecteur.')
            if uid in hub.tags and uid != previous:
                raise web.HTTPConflict(text='Cet UID est déjà attribué sur ce lecteur. Utilise Modifier.')
            if previous and previous != uid:
                hub.tags.pop(previous)
                if previous in hub.disabled:
                    hub.disabled[uid] = hub.disabled.pop(previous)
            hub.upsert(uid, name)
        elif action == 'enroll':
            if hub.enrolling:
                raise web.HTTPConflict(text='Un enregistrement attend déjà un badge. Annule-le d’abord.')
            hub.enroll(name)
        elif action == 'cancel':
            hub.cancel_enrollment()
        elif action == 'remove':
            hub.remove(uid)
        elif action == 'toggle':
            enabled = payload.get('enabled')
            seconds = payload.get('seconds', 0)
            if type(enabled) is not bool or type(seconds) is not int or seconds not in (0, 900, 3600, 86400):
                raise web.HTTPBadRequest(text='Durée de désactivation invalide.')
            if enabled:
                hub.disabled.pop(uid, None)
            else:
                hub.disabled[uid] = time() + seconds if seconds else None
            hub.save()
            hub.changed()
        elif action == 'rename_reader':
            self.hass.config_entries.async_update_entry(hub.entry, title=name)
            registry = dr.async_get(self.hass)
            device = registry.async_get_device(identifiers={(DOMAIN, hub.entry.entry_id)})
            if device:
                registry.async_update_device(device.id, name=name)
            hub.changed()
        else:
            raise web.HTTPBadRequest(text='Action inconnue.')
        # Persist the change before acknowledging it to the administrator.
        await hub.store.async_save(hub.stored_data())
        return self.json(reader_data(hub))
