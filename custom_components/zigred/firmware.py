"""Versioned release discovery, checksum verification and the USB installer panel."""
from datetime import timedelta
import hashlib
import json
import logging
from pathlib import Path
import re

import aiohttp
from aiohttp import web
from homeassistant.components import panel_custom
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

DATA_FIRMWARE = 'zigred_firmware'
REPOSITORY = 'zaraclem/ZigRed'
BOARD = 'esp32h2-devkitm-1-4mb'
LOGGER = logging.getLogger(__name__)


class FirmwareManager(DataUpdateCoordinator):
    def __init__(self, hass):
        super().__init__(hass, LOGGER, name='ZigRed firmware', update_interval=timedelta(hours=6))
        self.session = async_get_clientsession(hass)
        self.cache = {}

    async def read_url(self, url, maximum):
        async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=90)) as response:
            response.raise_for_status()
            result = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                result.extend(chunk)
                if len(result) > maximum:
                    raise ValueError('Firmware asset exceeds size limit')
            return bytes(result)

    async def _async_update_data(self):
        try:
            release = json.loads(await self.read_url(f'https://api.github.com/repos/{REPOSITORY}/releases/latest', 131072))
            # Integration-only releases do not carry a reader firmware.
            if not any(item['name'] == 'firmware.json' for item in release['assets']):
                release = await self.find_firmware_release()
            assets = {item['name']: item for item in release['assets']}
            descriptor = json.loads(await self.read_url(assets['firmware.json']['browser_download_url'], 16384))
            if (descriptor['board'] != BOARD or descriptor['hardware_version'] != 1
                    or descriptor['manufacturer_code'] != 0xFFF1 or descriptor['image_type'] != 0x5A52
                    or not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}', descriptor['version'])):
                raise ValueError('Firmware targets an unsupported reader')
            if release['tag_name'] != 'v' + descriptor['version']:
                raise ValueError('Release version does not match descriptor')
            major, minor, patch = map(int, descriptor['version'].split('.'))
            if max(major, minor, patch) > 255 or descriptor['file_version'] != (major << 24 | minor << 16 | patch << 8):
                raise ValueError('Invalid OTA file version')
            for kind, name in [('usb', 'zigred-h2-usb.bin'), ('ota', 'zigred-h2.ota')]:
                info = descriptor[kind]
                actual = assets[name]
                if (info['name'] != name or info['url'] != actual['browser_download_url']
                        or not 0 < info['size'] <= 4 * 1024 * 1024
                        or info['size'] != actual['size']
                        or not re.fullmatch(r'[a-f0-9]{64}', info['sha256'])):
                    raise ValueError('Invalid release asset metadata')
            descriptor['release_url'] = release['html_url']
            return descriptor
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise UpdateFailed('Firmware release unavailable or invalid; check GitHub Actions and repository visibility') from error

    async def find_firmware_release(self):
        for page in range(1, 11):
            releases = json.loads(await self.read_url(
                f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=30&page={page}',
                1024 * 1024))
            for release in releases:
                if not release['draft'] and not release['prerelease'] and any(
                        item['name'] == 'firmware.json' for item in release['assets']):
                    return release
            if len(releases) < 30:
                break
        raise ValueError('No published reader firmware found')

    async def asset(self, kind):
        if kind not in ('usb', 'ota') or not self.data or not self.last_update_success:
            raise ValueError('No verified firmware release available')
        metadata = self.data[kind]
        key = metadata['sha256']
        if key not in self.cache:
            raw = await self.read_url(metadata['url'], 4 * 1024 * 1024)
            if len(raw) != metadata['size'] or hashlib.sha256(raw).hexdigest() != key:
                raise ValueError('Firmware checksum mismatch')
            self.cache = {key: raw}
        return self.cache[key]


def require_admin(request):
    user = request.get('hass_user')
    if not user or not user.is_admin:
        raise web.HTTPForbidden()


class FirmwareInfoView(HomeAssistantView):
    url = '/api/zigred/firmware'
    name = 'api:zigred:firmware'
    requires_auth = True

    def __init__(self, manager):
        self.manager = manager

    async def get(self, request):
        require_admin(request)
        await self.manager.async_request_refresh()
        if not self.manager.last_update_success or not self.manager.data:
            raise web.HTTPServiceUnavailable(text='Aucune version firmware publiée ou accessible. Consulter GitHub Actions.')
        return self.json(self.manager.data)


class FirmwareAssetView(HomeAssistantView):
    url = '/api/zigred/firmware/{kind}'
    name = 'api:zigred:firmware:asset'
    requires_auth = True

    def __init__(self, manager):
        self.manager = manager

    async def get(self, request, kind):
        require_admin(request)
        try:
            return web.Response(body=await self.manager.asset(kind), content_type='application/octet-stream')
        except (aiohttp.ClientError, TimeoutError, ValueError) as error:
            raise web.HTTPServiceUnavailable(text='Impossible de télécharger et vérifier le firmware.') from error


async def async_setup_firmware(hass):
    if DATA_FIRMWARE in hass.data:
        return hass.data[DATA_FIRMWARE]
    manager = FirmwareManager(hass)
    await hass.http.async_register_static_paths([StaticPathConfig(
        '/zigred_static', str(Path(__file__).parent / 'frontend'), False), StaticPathConfig(
        '/zigred_brand', str(Path(__file__).parent / 'brand'), False)])
    hass.http.register_view(FirmwareInfoView(manager))
    hass.http.register_view(FirmwareAssetView(manager))
    from .converter import ConverterView
    hass.http.register_view(ConverterView(hass))
    from .readers import ReadersView
    hass.http.register_view(ReadersView(hass))
    await panel_custom.async_register_panel(hass, frontend_url_path='zigred',
        webcomponent_name='zigred-panel', sidebar_title='ZigRed', sidebar_icon='mdi:nfc',
        module_url='/zigred_static/panel.js?v=0.5.0', require_admin=True)
    hass.data[DATA_FIRMWARE] = manager
    # GitHub availability must not delay or prevent the sidebar from loading.
    hass.async_create_task(manager.async_refresh())
    return manager
