"""Check OTA file layout, hardware targeting and immutable release descriptors."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/package_firmware.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class FirmwarePackageTests(unittest.TestCase):
    def test_standard_header_and_application_element(self):
        config = json.loads((ROOT / 'firmware/version.json').read_text())
        app = b'\xe9' + b'firmware payload'
        image = packager.ota_image(app, config)
        header = struct.unpack('<IHHHHHIH32sIHH', image[:60])
        self.assertEqual(header[:6], (0x0BEEF11E, 0x100, 60, 4, 0xFFF1, 0x5A52))
        self.assertEqual(header[6], 0x00030000)
        self.assertEqual(header[-3:], (len(image), 1, 1))
        self.assertEqual(struct.unpack('<HI', image[60:66]), (0, len(app)))
        self.assertEqual(image[66:], app)

    def test_version_order_and_bounds(self):
        self.assertLess(packager.version_number('0.3.0'), packager.version_number('0.3.1'))
        for version in ['1.2', '-1.2.3', '1.2.256']:
            with self.assertRaises(ValueError):
                packager.version_number(version)

    def test_reject_app_that_does_not_fit_partition(self):
        config = json.loads((ROOT / 'firmware/version.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / 'ZigRed_H2.ino.bin').write_bytes(b'\xe9' * (0x140000 + 1))
            with self.assertRaises(ValueError):
                packager.package(folder, folder / 'dist', config)


if __name__ == '__main__':
    unittest.main()
