"""Tests autonomes de la logique MQTT/présence, sans installation Home Assistant."""
import importlib.util
import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from time import monotonic


def module(name, **attributes):
    result = types.ModuleType(name)
    result.__dict__.update(attributes)
    sys.modules[name] = result
    return result


class FakeStore:
    def __init__(self, *_args):
        self.saved = None

    async def async_load(self):
        return self.saved

    def async_delay_save(self, producer, _delay):
        self.saved = producer()


module('homeassistant')
module('homeassistant.components')
module('homeassistant.components.mqtt')
module('homeassistant.components.sensor', SensorEntity=object)
module('homeassistant.components.binary_sensor', BinarySensorEntity=object)
module('homeassistant.core', callback=lambda f: f)
module('homeassistant.helpers')
module('homeassistant.helpers.event', async_track_time_interval=lambda *_: lambda: None)
module('homeassistant.helpers.storage', Store=FakeStore)

component = Path(__file__).resolve().parents[1] / 'custom_components' / 'zigred'
spec = importlib.util.spec_from_file_location(
    'zigred', component / '__init__.py',
    submodule_search_locations=[str(component)],
)
integration = importlib.util.module_from_spec(spec)
sys.modules['zigred'] = integration
spec.loader.exec_module(integration)
sensor = importlib.import_module('zigred.sensor')
binary_sensor = importlib.import_module('zigred.binary_sensor')


class ReaderHubTests(unittest.TestCase):
    def setUp(self):
        entry = types.SimpleNamespace(entry_id='one', data={'topic': 'zigbee2mqtt/zigred'})
        self.hub = integration.ReaderHub(object(), entry)

    def send(self, uid, seq, *, retain=False):
        payload = json.dumps({'uid': uid, 'scan_seq': seq})
        self.hub.received(types.SimpleNamespace(payload=payload, retain=retain))

    def test_enroll_presence_rename_remove_and_replay(self):
        uid = 'A:04AABBCC'
        self.hub.pending_name = ' Mon badge '
        self.hub.enrolling = True
        self.send(uid, 1)
        self.assertEqual(self.hub.tags[uid], 'Mon badge')
        self.assertIn(uid, self.hub.active)
        self.assertEqual(self.hub.store.saved['tags'][uid], 'Mon badge')

        self.hub.active[uid] = monotonic() - 4
        self.send(uid, 1)
        self.hub.expire(None)
        self.assertNotIn(uid, self.hub.active)
        self.send(uid, 2)
        self.assertIn(uid, self.hub.active)

        self.hub.pending_name = 'Nouveau nom'
        self.hub.rename_selected()
        self.assertEqual(self.hub.tags[uid], 'Nouveau nom')
        self.hub.remove(uid)
        self.assertNotIn(uid, self.hub.tags)
        self.assertIn(uid, self.hub.active)  # deleting a name does not remove the physical badge

    def test_held_and_known_tags_do_not_consume_enrollment(self):
        held = 'A:04AABBCC'
        new = 'V:E00401502A49F6D0'
        self.send(held, 1)
        self.hub.enrolling = True
        self.hub.enroll_ignored = set(self.hub.active)
        self.send(held, 2)
        self.assertTrue(self.hub.enrolling)
        self.hub.pending_name = 'RFID V'
        self.send(new, 3)
        self.assertEqual(self.hub.tags[new], 'RFID V')

    def test_invalid_and_retained_payloads(self):
        self.hub.enrolling = True
        uid = 'A:04AABBCC'
        self.send(uid, 1, retain=True)
        self.send(uid, True)
        self.send('A:001122334455', 2)
        self.hub.received(types.SimpleNamespace(payload='[]', retain=False))
        self.hub.received(types.SimpleNamespace(payload='not json', retain=False))
        self.assertEqual(self.hub.tags, {})
        self.send(uid, 3)
        self.assertEqual(list(self.hub.tags), [uid])

    def test_firmware_metadata_does_not_create_presence(self):
        self.hub.received(types.SimpleNamespace(payload=json.dumps({
            'file_version': 0x00030000, 'ota_capable': True,
            'update': {'state': 'updating', 'progress': 42}}), retain=True))
        self.assertEqual(self.hub.firmware_version, '0.3.0')
        self.assertTrue(self.hub.ota_capable)
        self.assertEqual(self.hub.update_progress, 42)
        self.assertEqual(self.hub.active, {})

    def test_ota_responses_are_scoped_to_one_reader(self):
        self.hub.update_state = 'scheduled'
        self.hub.update_response(types.SimpleNamespace(payload=json.dumps({
            'data': {'id': 'another-reader'}, 'status': 'error', 'error': 'offline'})))
        self.assertEqual(self.hub.update_state, 'scheduled')
        self.hub.update_response(types.SimpleNamespace(payload=json.dumps({
            'data': {'id': 'zigred'}, 'status': 'error', 'error': 'offline'})))
        self.assertEqual(self.hub.update_state, 'idle')
        self.assertEqual(self.hub.update_error, 'offline')

    def test_read_only_entities_show_current_person_badge_and_presence(self):
        alice = 'A:04AABBCC'
        unknown = 'V:E00401502A49F6D0'
        person = sensor.CurrentPersonSensor(self.hub)
        badge = sensor.CurrentBadgeSensor(self.hub)
        present = binary_sensor.BadgePresentEntity(self.hub)
        self.assertEqual(person.native_value, 'Aucun')
        self.assertEqual(badge.native_value, 'Aucun')
        self.assertFalse(present.is_on)

        self.hub.tags[alice] = 'Alice'
        self.send(alice, 1)
        self.assertEqual(person.native_value, 'Alice')
        self.assertEqual(badge.native_value, alice)
        self.assertTrue(present.is_on)

        self.send(unknown, 2)
        self.assertEqual(person.native_value, 'Badge inconnu')
        self.assertEqual(badge.native_value, unknown)
        self.hub.active[unknown] = monotonic() - 4
        self.hub.expire(None)
        self.assertEqual(person.native_value, 'Alice')
        self.hub.active[alice] = monotonic() - 4
        self.hub.expire(None)
        self.assertEqual(person.native_value, 'Aucun')
        self.assertEqual(badge.native_value, 'Aucun')
        self.assertFalse(present.is_on)


if __name__ == '__main__':
    unittest.main()
