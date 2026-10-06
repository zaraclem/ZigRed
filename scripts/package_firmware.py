"""Build Zigbee OTA and USB release descriptors from Arduino output."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
ROOT=Path(__file__).resolve().parents[1]

def version_number(version):
    parts=[int(x) for x in version.split('.')]
    if len(parts)!=3 or any(not 0<=x<=255 for x in parts):
        raise ValueError('Use major.minor.patch, each number between 0 and 255')
    return (parts[0]<<24)|(parts[1]<<16)|(parts[2]<<8)

def ota_image(app,config):
    element=struct.pack('<HI',0,len(app))+app
    description=f"ZigRed {config['version']}".encode('ascii').ljust(32,b'\0')
    header=struct.pack('<IHHHHHIH32sIHH',0x0BEEF11E,0x0100,60,4,
        config['manufacturer_code'],config['image_type'],version_number(config['version']),
        2,description,60+len(element),config['hardware_version'],config['hardware_version'])
    return header+element

def write_version(config):
    (ROOT/'firmware/ZigRed_H2/version.h').write_text(
        '#pragma once\n'
        f'#define ZIGRED_VERSION "{config["version"]}"\n'
        f'#define ZIGRED_FILE_VERSION 0x{version_number(config["version"]):08X}UL\n'
        f'#define ZIGRED_HW_VERSION {config["hardware_version"]}\n'
        f'#define ZIGRED_MANUFACTURER {config["manufacturer_code"]}\n'
        f'#define ZIGRED_IMAGE_TYPE {config["image_type"]}\n',encoding='utf-8')

def package(build,output,config):
    data=(build/'ZigRed_H2.ino.bin').read_bytes()
    if not data or data[0]!=0xE9 or len(data)>0x140000:raise ValueError('Invalid or oversized ESP application')
    output.mkdir(parents=True,exist_ok=True)
    usb=output/'zigred-h2-usb.bin';ota=output/'zigred-h2.ota'
    shutil.copyfile(build/'ZigRed_H2.ino.merged.bin',usb)
    ota.write_bytes(ota_image(data,config))
    base=f'https://github.com/zaraclem/ZigRed/releases/download/v{config["version"]}/'
    result=dict(config,file_version=version_number(config['version']))
    for kind,path in [('usb',usb),('ota',ota)]:
        result[kind]={'name':path.name,'url':base+path.name,'size':path.stat().st_size,
                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (output/'firmware.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--build',type=Path,default=ROOT/'build');parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args();config=json.loads((ROOT/'firmware/version.json').read_text(encoding='utf-8-sig'))
    if args.prepare:write_version(config)
    else:package(args.build,args.output,config)
