// Zigbee2MQTT external converter for the ZigRed ESP32-H2 prototype.
// Protocol: custom cluster 0xFF00, attribute 0 = ZCL string "A:<UID>" or "V:<UID>".
const {Zcl} = require('zigbee-herdsman');
const {deviceAddCustomCluster} = require('zigbee-herdsman-converters/lib/modernExtend');
const exposes = require('zigbee-herdsman-converters/lib/exposes');
const e = exposes.presets;
const ea = exposes.access;
let scanCounter = 0;

function asString(value) {
    if (typeof value === 'string') return value;
    if (Buffer.isBuffer(value)) return value.toString('utf8');
    if (Array.isArray(value)) return Buffer.from(value).toString('utf8');
    return '';
}

module.exports = {
    zigbeeModel: ['ZigRed-H2', 'THZReader-H2'],
    model: 'ZigRed-H2',
    vendor: 'DIY',
    description: 'ESP32-H2 Zigbee reader with PN5180 (ISO14443A and ISO15693)',
    ota: true,
    extend: [deviceAddCustomCluster('thzReader', {
        name: 'thzReader', ID: 0xff00,
        attributes: {tag: {name: 'tag', ID: 0x0000, type: Zcl.DataType.CHAR_STR},
            firmwareVersion: {name: 'firmwareVersion', ID: 1, type: Zcl.DataType.UINT32},
            otaCapable: {name: 'otaCapable', ID: 2, type: Zcl.DataType.BOOLEAN},
            ledConfig: {name: 'ledConfig', ID: 3, type: Zcl.DataType.CHAR_STR},
            badgeFeedback: {name: 'badgeFeedback', ID: 4, type: Zcl.DataType.CHAR_STR},
            ledCapable: {name: 'ledCapable', ID: 5, type: Zcl.DataType.BOOLEAN}},
        commands: {}, commandsResponse: {},
    })],
    fromZigbee: [{
        cluster: 'thzReader', type: ['attributeReport', 'readResponse'],
        convert: (_model, msg) => {
            const raw = asString(msg.data.tag ?? msg.data[0]);
            const firmware = msg.data.firmwareVersion ?? msg.data[1];
            const metadata = {};
            if (Number.isInteger(firmware) && firmware >= 0 && firmware <= 0xffffffff) {
                metadata.file_version = firmware;
                metadata.firmware_version = `${firmware >>> 24}.${(firmware >>> 16) & 255}.${(firmware >>> 8) & 255}`;
                metadata.ota_capable = true;
                metadata.led_capable = firmware >= 0x00050000;
            }
            const config = msg.data.ledConfig ?? msg.data[3];
            if (config !== undefined) metadata.led_config = asString(config);
            const capable = msg.data.ledCapable ?? msg.data[5];
            if (capable !== undefined) metadata.led_capable = !!capable;
            // Attribute reads are not fresh RFID detections.
            if (msg.type === 'readResponse') return Object.keys(metadata).length ? metadata : undefined;
            const match = /^(?:A:(?:[0-9A-F]{8}|[0-9A-F]{14})|V:[0-9A-F]{16})$/.exec(raw);
            if (!match) return Object.keys(metadata).length ? metadata : undefined;
            scanCounter = (scanCounter + 1) % 2147483647;
            return {...metadata, uid: raw, protocol: raw[0] === 'A' ? 'ISO14443A' : 'ISO15693', scan_seq: scanCounter};
        },
    }],
    toZigbee: [{
        key: ['led_config', 'badge_feedback'],
        convertGet: async (entity, key) => {
            if (key === 'led_config') await entity.read(0xff00, [3]);
        },
        convertSet: async (entity, key, value) => {
            if (typeof value !== 'string') throw new Error('Expected a string');
            if (key === 'led_config') {
                if (!/^01[0-9A-Fa-f]{70}$/.test(value)) throw new Error('Invalid LED settings');
                await entity.write(0xff00, {3: {value, type: Zcl.DataType.CHAR_STR}});
                const result = await entity.read(0xff00, [3]);
                return {state: {led_config: asString(result.ledConfig ?? result[3])}};
            }
            if (!/^(?:A:(?:[0-9A-F]{8}|[0-9A-F]{14})|V:[0-9A-F]{16})\|(authorized|denied|unknown)$/.test(value)) {
                throw new Error('Invalid badge verdict');
            }
            await entity.write(0xff00, {4: {value, type: Zcl.DataType.CHAR_STR}});
        },
    }],
    configure: async (device) => {
        const endpoint = device.getEndpoint(1);
        const version = await endpoint.read('thzReader', ['firmwareVersion', 'otaCapable']);
        if ((version.firmwareVersion ?? version[1]) >= 0x00050000) {
            await endpoint.read(0xff00, [3, 5]);
        }
    },
    exposes: [
        e.text('uid', ea.STATE).withDescription('UID currently seen; repeated while the tag remains in range'),
        e.text('protocol', ea.STATE).withDescription('ISO14443A or ISO15693'),
        e.numeric('scan_seq', ea.STATE).withDescription('Changes only when a fresh RF reading is reported'),
        e.numeric('file_version', ea.STATE).withDescription('Zigbee OTA firmware version'),
        e.text('firmware_version', ea.STATE).withDescription('Installed ZigRed firmware'),
        e.text('led_config', ea.ALL).withDescription('LED settings managed from the ZigRed panel'),
        e.text('badge_feedback', ea.SET).withDescription('HA verdict for the UID currently read'),
    ],
};
