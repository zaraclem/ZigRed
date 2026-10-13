"""Replace the PN5180 host transport with ZigRed's independent GPIO driver.

RF protocol sources retain the upstream LGPL license. No Arduino SPI operations
remain in PN5180.cpp; bounded RF waits are supplied by patch_pn5180.py first.
"""
from pathlib import Path
import re
import shutil
import sys

root = Path(sys.argv[1])
source = root / 'PN5180.cpp'
code = source.read_text()
code = code.replace('#include "PN5180.h"', '#include "PN5180.h"\n#include "ZigRedPNTransport.h"')
code = code.replace('  SPI.begin();', '  ZigRedPNTransport(PN5180_NSS, PN5180_BUSY, PN5180_RST).begin();')
code = re.sub(r'^\s*SPI\.(?:beginTransaction|endTransaction|end)\([^\n]*\);', '', code, flags=re.M)
start = code.index('bool PN5180::transceiveCommand(')
end = code.index('void PN5180::reset()', start)
code = code[:start] + '''bool PN5180::transceiveCommand(uint8_t *sendBuffer, size_t sendBufferLen, uint8_t *recvBuffer, size_t recvBufferLen) {
  if (transportFailed) return false;
  ZigRedPNTransport transport(PN5180_NSS, PN5180_BUSY, PN5180_RST);
  bool ok = transport.exchange(sendBuffer, sendBufferLen, recvBuffer, recvBufferLen);
  if (!ok) transportFailed = true;
  return ok;
}

''' + code[end:]
source.write_text(code)
shutil.copyfile(Path(__file__).resolve().parents[1] / 'drivers/zigred_pn5180/ZigRedPNTransport.h', root / 'ZigRedPNTransport.h')
print('PN5180 host transport: ZigRed GPIO SPI mode 0, half-period >=2 us')
