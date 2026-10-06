const assert = require('node:assert/strict');
const Module = require('node:module');

const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
    if (request === 'zigbee-herdsman') return {Zcl: {DataType: {CHAR_STR: 1}}};
    if (request === 'zigbee-herdsman-converters/lib/modernExtend') {
        return {deviceAddCustomCluster: () => ({})};
    }
    if (request === 'zigbee-herdsman-converters/lib/exposes') {
        const expose = () => ({withDescription() { return this; }});
        return {presets: {text: expose, numeric: expose}, access: {STATE: 1}};
    }
    return originalLoad(request, parent, isMain);
};

const definition = require('../zigbee2mqtt/zigred.js');
Module._load = originalLoad;
assert.equal(definition.model, 'ZigRed-H2');
const converter = definition.fromZigbee[0];
assert.deepEqual(converter.type, ['attributeReport', 'readResponse']);

function report(tag) {
    return converter.convert(null, {data: {tag}});
}

const a = report('A:04AABBCC');
assert.equal(a.protocol, 'ISO14443A');
assert.equal(a.uid, 'A:04AABBCC');
assert.equal(report('A:00112233445566').scan_seq, a.scan_seq + 1);
assert.equal(report('V:E00401502A49F6D0').protocol, 'ISO15693');
for (const invalid of ['A:00112233445566778899', 'A:001122334455',
    'V:00112233', 'A:04aabbcc', 'x', '']) {
    assert.equal(report(invalid), undefined, invalid);
}
console.log('Convertisseur Zigbee2MQTT : OK');
assert.equal(definition.ota, true);
assert.deepEqual(converter.convert(null, {type:'attributeReport',data:{firmwareVersion:0x00030000}}),
    {file_version:0x00030000,firmware_version:'0.3.0',ota_capable:true});
assert.equal(converter.convert(null, {type:'readResponse',data:{tag:'A:04AABBCC'}}), undefined);
