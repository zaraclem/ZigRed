"""Identify paired readers from Zigbee2MQTT's retained device inventory."""
import asyncio
import json
import re

from homeassistant.components import mqtt
from homeassistant.core import callback

MODELS = {'ZigRed-H2', 'THZReader-H2'}
IEEE_RE = re.compile(r'^0x[0-9a-f]{16}$')


def valid_base(base):
    return isinstance(base, str) and bool(base) and not any(c in base for c in ('+', '#', '\x00'))


def paired_readers(payload):
    if len(payload) > 1024 * 1024:
        raise ValueError('Device inventory exceeds size limit')
    devices = json.loads(payload)
    if not isinstance(devices, list):
        raise ValueError('Invalid device inventory')
    result = {}
    for device in devices:
        if not isinstance(device, dict):
            continue
        definition = device.get('definition') or {}
        if not isinstance(definition, dict):
            continue
        model = definition.get('model') or device.get('model_id')
        address = str(device.get('ieee_address', '')).lower()
        friendly = device.get('friendly_name') or address
        interviewed = device.get('interview_state') == 'SUCCESSFUL' or (
            'interview_state' not in device and device.get('interview_completed') is True)
        if (model not in MODELS or not IEEE_RE.fullmatch(address) or not interviewed
                or device.get('disabled') is True or not valid_base(friendly)):
            continue
        result[address] = {'ieee_address': address, 'friendly_name': friendly,
                           'model': model, 'supported': device.get('supported') is True}
    return result


async def discover(hass, base):
    future = asyncio.get_running_loop().create_future()

    @callback
    def received(message):
        if future.done():
            return
        try:
            future.set_result(paired_readers(message.payload))
        except (ValueError, TypeError):
            future.set_exception(ValueError('Invalid Zigbee2MQTT device inventory'))

    unsubscribe = await mqtt.async_subscribe(hass, f'{base}/bridge/devices', received, qos=1)
    try:
        return await asyncio.wait_for(future, timeout=10)
    finally:
        unsubscribe()
