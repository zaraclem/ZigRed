// Same GPIO transport as production ZigRed 0.5.3, no Zigbee/RF/LED.
#include <Arduino.h>
#include "ZigRedPNTransport.h"
static void runDiagnostic() {
  const unsigned delays[]={2,10};
  for(unsigned halfUs:delays)for(int strict=0;strict<2;strict++) {
    ZigRedPNTransport transport(1,10,11,halfUs);
    transport.begin();transport.reset();
    Serial.printf("\r\n--- GPIO SPI half-period >=%u us / response %s ---\r\n",halfUs,strict?"strict":"release NSS");
    const uint8_t irqCmd[]={0x04,0x02};uint8_t irq[4]={};
    bool ok=transport.exchange(irqCmd,2,irq,4,strict);
    Serial.printf("IRQ exchange %s; RX %02X %02X %02X %02X\r\n",ok?"OK":"FAIL",irq[0],irq[1],irq[2],irq[3]);
    if(!ok)transport.reset();
    const uint8_t cmd[]={0x07,0x12,0x02};uint8_t a[2]={},b[2]={};
    bool first=transport.exchange(cmd,3,a,2,strict);
    bool second=first&&transport.exchange(cmd,3,b,2,strict);
    bool valid=first&&second&&a[0]==b[0]&&a[1]==b[1]&&
      !(a[0]==0&&a[1]==0)&&!(a[0]==255&&a[1]==255);
    Serial.printf("EEPROM: %02X %02X / %02X %02X; %s; firmware candidate %u.%u\r\n",
      a[0],a[1],b[0],b[1],valid?"STABLE":"FAIL/INVALID",a[1],a[0]);
    delay(100);
  }
  Serial.println("DONE. Send r to repeat. GPIO SPI only: no badges, RF, Zigbee or LED.");
}
void setup(){Serial.begin(115200);delay(3000);Serial.println("\r\nZigRed H2 DIAGNOSTIC 2 / GPIO SPI / SCK4 MOSI5 MISO0 NSS1 BUSY10 RST11");runDiagnostic();}
void loop(){if(Serial.available()&&Serial.read()=='r')runDiagnostic();delay(10);}