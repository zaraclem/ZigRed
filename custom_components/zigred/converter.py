"""Install the bundled converter through Zigbee2MQTT's MQTT API."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from aiohttp import web
from homeassistant.components import mqtt
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback

from .const import DOMAIN
from .discovery import valid_base


class ConverterView(HomeAssistantView):
    url = '/api/zigred/converter'
    name = 'api:zigred:converter'
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass
        self.locks = {}

    def require_admin(self, request):
        user = request.get('hass_user')
        if not user or not user.is_admin:
            raise web.HTTPForbidden()

    async def get(self, request):
        self.require_admin(request)
        return self.json({'readers': [{'entry_id': hub.entry.entry_id,
            'name': hub.entry.title} for hub in self.hass.data.get(DOMAIN, {}).values()]})

    async def post(self, request):
        self.require_admin(request)
        try:
            payload = await request.json()
        except (ValueError, TypeError) as error:
            raise web.HTTPBadRequest(text='Demande invalide.') from error
        if not isinstance(payload, dict):
            raise web.HTTPBadRequest(text='Demande invalide.')
        if 'entry_id' in payload:
            if not isinstance(payload['entry_id'], str):
                raise web.HTTPBadRequest(text='Choisis un lecteur ZigRed.')
            hub = self.hass.data.get(DOMAIN, {}).get(payload['entry_id'])
            if hub is None:
                raise web.HTTPBadRequest(text='Ce lecteur ZigRed n’est plus configuré.')
            base = hub.base_topic
        else:
            base = payload.get('base_topic')
            if not valid_base(base) or base != base.strip().rstrip('/'):
                raise web.HTTPBadRequest(text='Indique le sujet de base Zigbee2MQTT.')
        lock = self.locks.setdefault(base, asyncio.Lock())
        if lock.locked():
            raise web.HTTPConflict(text='Une installation est déjà en cours pour ce Zigbee2MQTT.')
        async with lock:
            code = await self.hass.async_add_executor_job(
                lambda: (Path(__file__).parent / 'zigbee2mqtt' / 'zigred.js').read_text(encoding='utf-8'))
            transaction = uuid4().hex
            result = asyncio.get_running_loop().create_future()

            @callback
            def received(message):
                if message.retain:
                    return
                try:
                    response = json.loads(message.payload)
                except (TypeError, ValueError):
                    return
                if (isinstance(response, dict) and response.get('transaction') == transaction
                        and not result.done()):
                    result.set_result(response)

            unsubscribe = await mqtt.async_subscribe(self.hass,
                f'{base}/bridge/response/converter/save', received, qos=1)
            try:
                await mqtt.async_publish(self.hass, f'{base}/bridge/request/converter/save',
                    json.dumps({'name': 'zigred.js', 'code': code, 'transaction': transaction}),
                    qos=1, retain=False)
                response = await asyncio.wait_for(result, timeout=30)
            except TimeoutError as error:
                raise web.HTTPGatewayTimeout(text='Zigbee2MQTT n’a pas répondu. Vérifie qu’il est démarré, '
                    'connecté au même serveur MQTT et que advanced.enable_external_js est activé.') from error
            finally:
                unsubscribe()
            if response.get('status') != 'ok':
                raise web.HTTPBadGateway(text='Zigbee2MQTT a refusé le convertisseur : '
                    + str(response.get('error', 'consulte ses journaux'))[:1000])
            return self.json({'message': 'Convertisseur ZigRed enregistré et chargé par Zigbee2MQTT.'})
