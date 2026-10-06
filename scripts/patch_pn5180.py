"""Apply bounded host-interface waits to the pinned PN5180 1.8.1 driver.

The upstream library is LGPL-2.1-or-later. Its original headers and license
remain in the installed library. This script records our build-time changes.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
source = root / 'PN5180.cpp'
header = root / 'PN5180.h'
code = source.read_text(encoding='utf-8')
declarations = header.read_text(encoding='utf-8')

def replace_once(old, new):
    global code
    if code.count(old) != 1:
        raise RuntimeError(f'Pinned PN5180 source differs: {old[:80]}')
    code = code.replace(old, new, 1)

declarations = declarations.replace('  void begin();', '''  bool hasTransportError() const { return transportFailed; }
  void begin();''')
declarations = declarations.replace('  bool transceiveCommand(', '''  bool transportFailed = false;
  bool waitBusy(uint8_t level, const char *stage);
  bool waitIRQ(uint32_t mask, const char *stage);
  bool transceiveCommand(''')
replace_once('void PN5180::begin() {', 'void PN5180::begin() {\n  transportFailed = false;')
replace_once('SPISettings(7000000, MSBFIRST, SPI_MODE0)', 'SPISettings(1000000, MSBFIRST, SPI_MODE0)')

# Preserve transaction cleanup and expose failures to the protocol callers.
import re
code, count = re.subn(
    r'(?m)^(\s*)transceiveCommand\(([^\n]+)\);\n(\s*)SPI.endTransaction\(\);',
    r'\1bool commandOK = transceiveCommand(\2);\n\3SPI.endTransaction();\n\3if (!commandOK) return false;', code)
if count != 11:
    raise RuntimeError(f'Expected 11 transport callers, found {count}')
# readData returns a pointer.
start = code.index('uint8_t * PN5180::readData(')
end = code.index('bool PN5180::loadRFConfig(', start)
code = code[:start] + code[start:end].replace('if (!commandOK) return false;', 'if (!commandOK) return nullptr;') + code[end:]
replace_once('  uint32_t irqStatus;', '  uint32_t irqStatus = 0;')

helpers = '''bool PN5180::waitBusy(uint8_t level, const char *stage) {
  uint32_t started = millis();
  while (digitalRead(PN5180_BUSY) != level) {
    if (uint32_t(millis() - started) >= 250) {
      digitalWrite(PN5180_NSS, HIGH);
      transportFailed = true;
      Serial.printf("PN5180 timeout: %s; BUSY=%d expected=%d RST=%d\\n",
                    stage, digitalRead(PN5180_BUSY), level, digitalRead(PN5180_RST));
      return false;
    }
    delay(1);
  }
  return true;
}

bool PN5180::waitIRQ(uint32_t mask, const char *stage) {
  uint32_t started = millis();
  while (!transportFailed) {
    uint32_t irq = 0;
    if (!readRegister(IRQ_STATUS, &irq)) return false;
    // As in the filament reader, the awaited completion confirms success.
    // A sticky error from an earlier no-card exchange must not override it.
    if (irq & mask) return true;
    if ((irq & (1UL << 17)) && mask != IDLE_IRQ_STAT) {
      uint32_t system = 0, rf = 0, enabled = 0;
      readRegister(SYSTEM_STATUS, &system);
      readRegister(RF_STATUS, &rf);
      readRegister(IRQ_ENABLE, &enabled);
      Serial.printf("PN5180 rejected %s: IRQ=0x%08lX SYSTEM=0x%08lX RF=0x%08lX IRQ_ENABLE=0x%08lX\\n",
                    stage, (unsigned long)irq, (unsigned long)system,
                    (unsigned long)rf, (unsigned long)enabled);
      Serial.printf("PN5180 error: parameter=%d syntax=%d semantic=%d TVDD_OK=%d\\n",
                    !!(system & 0x100), !!(system & 0x80), !!(system & 0x40), !!(system & 0x200));
      transportFailed = true;
      return false;
    }
    if (uint32_t(millis() - started) >= 500) {
      transportFailed = true;
      Serial.printf("PN5180 timeout: %s; IRQ=0x%08lX\\n", stage, (unsigned long)irq);
      return false;
    }
    delay(1);
  }
  return false;
}

'''
replace_once('bool PN5180::transceiveCommand(uint8_t *sendBuffer, size_t sendBufferLen, uint8_t *recvBuffer, size_t recvBufferLen) {',
             helpers + 'bool PN5180::transceiveCommand(uint8_t *sendBuffer, size_t sendBufferLen, uint8_t *recvBuffer, size_t recvBufferLen) {\n  if (transportFailed) return false;')
waits = [
 ('while (LOW != digitalRead(PN5180_BUSY)); // wait until busy is low', 'if (!waitBusy(LOW, "before command")) return false;'),
 ('while(HIGH != digitalRead(PN5180_BUSY));  // wait until BUSY is high', 'if (!waitBusy(HIGH, "command accepted")) return false;'),
 ('while (LOW != digitalRead(PN5180_BUSY)); // wait unitl BUSY is low', 'if (!waitBusy(LOW, "command completed")) return false;'),
 ('while(HIGH != digitalRead(PN5180_BUSY));  // wait until BUSY is high', 'if (!waitBusy(HIGH, "response accepted")) return false;'),
 ('while(LOW != digitalRead(PN5180_BUSY));  // wait until BUSY is low', 'if (!waitBusy(LOW, "response completed")) return false;'),
]
for old, new in waits:
    if old not in code:
        raise RuntimeError('Missing BUSY wait: ' + old)
    code = code.replace(old, new, 1)
replace_once('while (0 == (IDLE_IRQ_STAT & getIRQStatus())); // wait for system to start up',
             'if (!waitIRQ(IDLE_IRQ_STAT, "reset IDLE IRQ")) return;')
replace_once('while (0 == (TX_RFON_IRQ_STAT & getIRQStatus())); // wait for RF field to set up',
             'if (!waitIRQ(TX_RFON_IRQ_STAT, "RF on IRQ")) return false;')
replace_once('while (0 == (TX_RFOFF_IRQ_STAT & getIRQStatus())); // wait for RF field to shut down',
             'if (!waitIRQ(TX_RFOFF_IRQ_STAT, "RF off IRQ")) return false;')
# Avoid writing reserved IRQ_CLEAR bits on newer PN5180 revisions.
code = code.replace('clearIRQStatus(0xffffffff)', 'clearIRQStatus(0x000fffff)')
# Scope each field-operation wait to its own flags, not the prior tag exchange.
replace_once('  uint8_t cmd[2] = { PN5180_RF_ON, 0x00 };',
             '  if (!clearIRQStatus(0x000fffff)) return false;\n  uint8_t cmd[2] = { PN5180_RF_ON, 0x00 };')
replace_once('  uint8_t cmd[2] { PN5180_RF_OFF, 0x00 };',
             '  if (!clearIRQStatus(0x000fffff)) return false;\n  uint8_t cmd[2] { PN5180_RF_OFF, 0x00 };')
source.write_text(code, encoding='utf-8')
header.write_text(declarations, encoding='utf-8')
for filename in ('PN5180ISO14443.cpp', 'PN5180ISO15693.cpp'):
    protocol_path = root / filename
    protocol = protocol_path.read_text(encoding='utf-8')
    protocol = protocol.replace('uint32_t rxStatus;', 'uint32_t rxStatus = 0;')
    if filename == 'PN5180ISO15693.cpp':
        old = '  while (0 == (status & RX_IRQ_STAT)) {\n    delay(10);\n    status = getIRQStatus();\n  }'
        new = '''  uint32_t receiveStarted = millis();
  while (0 == (status & RX_IRQ_STAT)) {
    if (hasTransportError()) return ISO15693_EC_UNKNOWN_ERROR;
    if (uint32_t(millis() - receiveStarted) >= 500) {
      Serial.println("PN5180 timeout: ISO15693 RX IRQ");
      return ISO15693_EC_UNKNOWN_ERROR;
    }
    delay(10);
    status = getIRQStatus();
  }'''
        if protocol.count(old) != 1:
            raise RuntimeError('Pinned ISO15693 receive loop differs')
        protocol = protocol.replace(old, new)
    protocol_path.write_text(protocol, encoding='utf-8')
print('PN5180: bounded BUSY/IRQ waits, propagated errors, SPI 1 MHz')
