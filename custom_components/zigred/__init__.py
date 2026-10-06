"""Persistent tag names and held-tag presence over Zigbee2MQTT MQTT messages."""
import json
import asyncio
import re
from datetime import timedelta
from time import monotonic, time

from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import DOMAIN, PLATFORMS, EXPIRY_SECONDS
from .discovery import paired_readers
from .led import DEFAULTS, validate_settings, encode_settings
from copy import deepcopy

UID_RE = re.compile(r'^(?:A:(?:[0-9A-F]{8}|[0-9A-F]{14})|V:[0-9A-F]{16})$')


class ReaderHub:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, 1, f'zigred_{entry.entry_id}')
        self.tags = {}  # UID -> display name; names are kept on HA, not the microcontroller
        self.disabled = {}  # UID -> Unix expiry or None for manual reactivation
        self.active = {}  # UID -> monotonic time of last received heartbeat
        self.last_uid = None
        self.last_seq = None
        self.pending_name = ''
        self.selected_uid = None
        self.enrolling = False
        self.enroll_deadline = 0
        self.enroll_ignored = set()
        self.listeners = set()
        self.unsub_mqtt = None
        self.unsub_timer = None
        self.unsub_update = None
        self.unsub_devices = None
        self.inventory_lock = asyncio.Lock()
        self.stopped = False
        self.paired = False
        self.converter_ready = False
        self.ieee_address = entry.data.get('ieee_address')
        self.topic = entry.data['topic']
        self.base_topic = entry.data.get('base_topic', entry.data['topic'].split('/')[0])
        self.device_id = entry.data.get('device_id', entry.data['topic'][len(self.base_topic) + 1:])
        self.firmware_version = None
        self.file_version = None
        self.ota_capable = False
        self.update_state = 'idle'
        self.update_progress = None
        self.update_error = None
        self.led_settings = deepcopy(DEFAULTS)
        self.led_capable = False
        self.led_applied = None
        self.led_error = None
        self.led_task = None
        self.led_signature = None
        self.led_last_config = 0

    def stored_data(self):
        return {'tags': self.tags, 'disabled': self.disabled, 'led': self.led_settings}

    async def sync_led(self, force=False):
        if self.stopped or not self.paired or not self.converter_ready or not self.led_capable:
            return
        encoded = encode_settings(self.led_settings)
        uid = next(reversed(self.active), None)
        state = 'unknown' if uid not in self.tags else 'authorized' if self.is_enabled(uid) else 'denied'
        signature = (uid, state, encoded)
        try:
            if force or (self.led_applied != encoded and monotonic() - self.led_last_config >= 30):
                self.led_last_config = monotonic()
                await mqtt.async_publish(self.hass, f'{self.topic}/set',
                    json.dumps({'led_config': encoded}), qos=1, retain=False)
            if uid and (force or signature != self.led_signature):
                await mqtt.async_publish(self.hass, f'{self.topic}/set',
                    json.dumps({'badge_feedback': f'{uid}|{state}'}), qos=1, retain=False)
            self.led_signature = signature
            self.led_error = None
        except Exception as error:
            self.led_error = str(error)

    def queue_led(self):
        if self.stopped:
            return
        if self.led_task is None or self.led_task.done():
            self.led_task = self.hass.async_create_task(self.sync_led())

    @property
    def current_uid(self):
        """Most recently read badge still considered present."""
        return next((uid for uid in reversed(self.active) if self.is_enabled(uid)), None)

    def is_enabled(self, uid):
        return uid not in self.disabled

    def save(self):
        self.store.async_delay_save(self.stored_data, 1)

    def upsert(self, uid, name):
        self.tags[uid] = name
        self.save()
        self.changed()

    def cancel_enrollment(self):
        self.enrolling = False
        self.pending_name = ''
        self.enroll_ignored.clear()
        self.enroll_deadline = 0
        self.changed()

    def enroll(self, name):
        self.pending_name = name
        self.enrolling = True
        self.enroll_ignored = set(self.active)
        self.enroll_deadline = monotonic() + 120
        self.changed()

    async def start(self):
        data = await self.store.async_load() or {}
        if not isinstance(data, dict) or not isinstance(data.get('tags', {}), dict):
            data = {}
        self.tags = {uid: name for uid, name in data.get('tags', {}).items()
                     if isinstance(uid, str) and UID_RE.fullmatch(uid) and isinstance(name, str)}
        try:
            self.led_settings = validate_settings(data.get('led', DEFAULTS))
        except ValueError:
            self.led_settings = deepcopy(DEFAULTS)
        disabled = data.get('disabled', {})
        if isinstance(disabled, dict):
            self.disabled = {uid: until for uid, until in disabled.items()
                             if uid in self.tags and (until is None or
                                (type(until) in (int, float) and until > time()))}
        self.unsub_mqtt = await mqtt.async_subscribe(
            self.hass, self.entry.data['topic'], self.received, qos=0)
        self.unsub_timer = async_track_time_interval(self.hass, self.expire, timedelta(seconds=1))
        self.unsub_update = await mqtt.async_subscribe(self.hass,
            f'{self.base_topic}/bridge/response/device/ota_update/update', self.update_response, qos=1)
        self.unsub_devices = await mqtt.async_subscribe(self.hass,
            f'{self.base_topic}/bridge/devices', self.inventory_received, qos=1)

    async def inventory_received(self, message):
        async with self.inventory_lock:
            if self.stopped:
                return
            try:
                devices = paired_readers(message.payload)
            except (ValueError, TypeError):
                return
            device = devices.get(self.ieee_address) if self.ieee_address else next((
                item for item in devices.values()
                if f"{self.base_topic}/{item['friendly_name']}" == self.topic), None)
            if device and any(entry.entry_id != self.entry.entry_id and
                    (entry.unique_id == device['ieee_address'] or
                     entry.data.get('ieee_address') == device['ieee_address'])
                    for entry in self.hass.config_entries.async_entries(DOMAIN)):
                device = None
            was_paired = self.paired
            self.paired = device is not None
            self.converter_ready = bool(device and device['supported'])
            if device:
                self.ieee_address = device['ieee_address']
                self.device_id = device['friendly_name']
                topic = f'{self.base_topic}/{self.device_id}'
                data = {**self.entry.data, 'topic': topic, 'device_id': self.device_id,
                        'ieee_address': self.ieee_address}
                self.hass.config_entries.async_update_entry(self.entry,
                    unique_id=self.ieee_address, data=data)
                if self.topic != topic or not was_paired:
                    if self.unsub_mqtt:
                        self.unsub_mqtt()
                    self.active.clear()
                    self.last_seq = None
                    self.topic = topic
                    unsubscribe = await mqtt.async_subscribe(
                        self.hass, topic, self.received, qos=0)
                    if self.stopped:
                        unsubscribe()
                    else:
                        self.unsub_mqtt = unsubscribe
            else:
                self.active.clear()
            self.changed()

    async def stop(self):
        self.stopped = True
        if self.led_task and not self.led_task.done():
            self.led_task.cancel()
        if self.unsub_devices:
            self.unsub_devices()
        if self.unsub_mqtt:
            self.unsub_mqtt()
        if self.unsub_timer:
            self.unsub_timer()
        if self.unsub_update:
            self.unsub_update()
        self.active.clear()

    @callback
    def changed(self):
        self.queue_led()
        for listener in tuple(self.listeners):
            listener()

    @callback
    def received(self, message):
        if not self.paired:
            return
        try:
            payload = json.loads(message.payload)
        except (TypeError, ValueError):
            return
        if not isinstance(payload, dict):
            return
        metadata_changed = False
        if type(payload.get('led_capable')) is bool:
            self.led_capable = payload['led_capable']
            metadata_changed = True
        if isinstance(payload.get('led_config'), str):
            self.led_applied = payload['led_config']
            metadata_changed = True
        version = payload.get('file_version')
        if type(version) is int and 0 <= version <= 0xFFFFFFFF:
            self.file_version = version
            self.firmware_version = f'{version >> 24}.{(version >> 16) & 255}.{(version >> 8) & 255}'
            self.ota_capable = payload.get('ota_capable', True) is True
            metadata_changed = True
        update = payload.get('update')
        if isinstance(update, dict) and update.get('state') in ('idle', 'available', 'scheduled', 'updating'):
            self.update_state = update['state']
            progress = update.get('progress')
            self.update_progress = progress if type(progress) in (int, float) and 0 <= progress <= 100 else None
            metadata_changed = True
        if metadata_changed:
            self.changed()
        if getattr(message, 'retain', False):
            return
        uid = payload.get('uid')
        if not isinstance(uid, str) or not UID_RE.fullmatch(uid):
            return
        seq = payload.get('scan_seq')
        if type(seq) is not int or seq < 0 or seq == self.last_seq:
            return
        self.last_seq = seq
        self.last_uid = uid
        if self.enrolling and uid not in self.enroll_ignored and uid not in self.tags:
            self.enrolling = False
            self.enroll_ignored.clear()
            self.tags[uid] = self.pending_name.strip()[:80] or uid
            self.selected_uid = uid
            self.save()
            self.pending_name = ''
        # Move this UID to the end so identical clock ticks still preserve
        # which badge was read most recently.
        self.active.pop(uid, None)
        self.active[uid] = monotonic()
        # Reply to each heartbeat so the verdict stays visible while held.
        self.led_signature = None
        self.changed()

    @callback
    def update_response(self, message):
        try:
            payload = json.loads(message.payload)
        except (TypeError, ValueError):
            return
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), dict):
            return
        if payload['data'].get('id') != self.device_id:
            return
        self.update_state = 'idle'
        self.update_error = payload.get('error') if payload.get('status') == 'error' else None
        self.changed()

    @callback
    def expire(self, now):
        current_time = monotonic()
        reenabled = [uid for uid, until in self.disabled.items()
                     if until is not None and time() >= until]
        for uid in reenabled:
            del self.disabled[uid]
        if reenabled:
            self.save()
        if self.enrolling and current_time >= self.enroll_deadline:
            self.cancel_enrollment()
        expired = [uid for uid, seen in self.active.items()
                   if current_time - seen >= EXPIRY_SECONDS]
        for uid in expired:
            del self.active[uid]
            self.enroll_ignored.discard(uid)
        if expired or reenabled:
            self.changed()
        elif self.led_capable and self.led_applied != encode_settings(self.led_settings):
            self.queue_led()

    def remove(self, uid):
        if uid not in self.tags:
            return
        del self.tags[uid]
        self.disabled.pop(uid, None)
        if self.selected_uid == uid:
            self.selected_uid = next(iter(self.tags), None)
        self.save()
        self.changed()

    def rename_selected(self):
        """Compatibility helper; the panel uses explicit reader/UID requests."""
        name = self.pending_name.strip()[:80]
        if self.selected_uid in self.tags and name:
            self.upsert(self.selected_uid, name)
            self.pending_name = ''


async def async_setup(hass, config):
    """Register the sidebar before starting any physical reader."""
    from .firmware import async_setup_firmware
    hass.data.setdefault(DOMAIN, {})
    await async_setup_firmware(hass)
    return True


async def async_setup_entry(hass, entry):
    from .firmware import async_setup_firmware
    await async_setup_firmware(hass)
    if entry.data.get('kind') == 'workspace':
        return True
    hub = ReaderHub(hass, entry)
    await hub.start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    # Remove the old configuration controls and per-person entities. Names and
    # UIDs remain in this reader's Store and are managed through the panel.
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    retained = {f'{entry.entry_id}_{suffix}' for suffix in
                ('current_person', 'current_badge', 'badge_present', 'firmware')}
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform == DOMAIN and entity.unique_id not in retained:
            registry.async_remove(entity.entity_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    if entry.data.get('kind') == 'workspace':
        return True
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hub = hass.data[DOMAIN].pop(entry.entry_id)
    await hub.stop()
    return True
