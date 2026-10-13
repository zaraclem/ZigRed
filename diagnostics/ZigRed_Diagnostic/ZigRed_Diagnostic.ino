// Standalone ESP32-H2 diagnostic: Arduino SPI only, no PN5180 library or Zigbee.
#include <Arduino.h>
#include <SPI.h>
constexpr int SCK_PIN=4, MOSI_PIN=5, MISO_PIN=0, NSS_PIN=1, BUSY_PIN=10, RST_PIN=11;
static bool waitBusy(int expected, const char *stage) {
  uint32_t start=millis();
  while(digitalRead(BUSY_PIN)!=expected) {
    if(uint32_t(millis()-start)>=250) {
      Serial.printf("FAIL %s BUSY=%d expected=%d NSS=%d RST=%d\r\n",stage,
        digitalRead(BUSY_PIN),expected,digitalRead(NSS_PIN),digitalRead(RST_PIN));
      digitalWrite(NSS_PIN,HIGH);return false;
    }
    delayMicroseconds(50);
  }
  return true;
}
static bool exchange(uint32_t speed, bool strict, const uint8_t *cmd,size_t n,uint8_t *out,size_t len) {
  SPI.beginTransaction(SPISettings(speed,MSBFIRST,SPI_MODE0));
  bool ok=false;
  do {
    if(!waitBusy(LOW,"before command"))break;
    digitalWrite(NSS_PIN,LOW);delay(2);
    for(size_t i=0;i<n;i++)SPI.transfer(cmd[i]);
    if(!waitBusy(HIGH,"command accepted"))break;
    digitalWrite(NSS_PIN,HIGH);delay(1);
    if(!waitBusy(LOW,"command completed"))break;
    digitalWrite(NSS_PIN,LOW);delay(2);
    for(size_t i=0;i<len;i++)out[i]=SPI.transfer(0xff);
    Serial.print("RX:");for(size_t i=0;i<len;i++)Serial.printf(" %02X",out[i]);Serial.println();
    // Compare the original library handshake with a response frame released
    // immediately after its bytes; never use this path for normal badge reads.
    if(strict&&!waitBusy(HIGH,"response accepted"))break;
    digitalWrite(NSS_PIN,HIGH);delay(1);
    if(!waitBusy(LOW,"response completed"))break;
    ok=true;
  } while(false);
  digitalWrite(NSS_PIN,HIGH);SPI.endTransaction();return ok;
}
static void resetPN() {
  digitalWrite(NSS_PIN,HIGH);digitalWrite(RST_PIN,LOW);delay(20);
  digitalWrite(RST_PIN,HIGH);delay(50);
  Serial.printf("RESET BUSY=%d MISO=%d\r\n",digitalRead(BUSY_PIN),digitalRead(MISO_PIN));
}
static void runDiagnostic() {
  const uint32_t speeds[]={100000,1000000,7000000};
  for(uint32_t speed:speeds)for(int mode=0;mode<2;mode++) {
    Serial.printf("\r\n--- SPI %lu Hz / response %s ---\r\n",(unsigned long)speed,mode==0?"strict":"release NSS");
    resetPN();
    uint8_t irq[4]={};const uint8_t irqCmd[]={0x04,0x02};
    bool irqOK=exchange(speed,mode==0,irqCmd,sizeof(irqCmd),irq,sizeof(irq));
    Serial.printf("IRQ exchange %s\r\n",irqOK?"OK":"FAIL");
    if(!irqOK)resetPN();
    uint8_t first[2]={},second[2]={};const uint8_t versionCmd[]={0x07,0x12,0x02};
    bool a=exchange(speed,mode==0,versionCmd,sizeof(versionCmd),first,sizeof(first));
    bool b=a&&exchange(speed,mode==0,versionCmd,sizeof(versionCmd),second,sizeof(second));
    bool credible=a&&b&&first[0]==second[0]&&first[1]==second[1]&&
      !(first[0]==0&&first[1]==0)&&!(first[0]==0xff&&first[1]==0xff);
    Serial.printf("EEPROM repeated %s; firmware candidate %u.%u (not a badge test)\r\n",
      credible?"STABLE":"FAIL/INVALID",first[1],first[0]);
    delay(100);
  }
  Serial.println("\r\nDONE. Send r to repeat. No RF field, badge reading, LED or Zigbee in this firmware.");
}
void setup() {
  Serial.begin(115200);delay(3000);
  Serial.println("\r\nZigRed H2 DIAGNOSTIC 1 / SCK4 MOSI5 MISO0 NSS1 BUSY10 RST11");
  pinMode(NSS_PIN,OUTPUT);digitalWrite(NSS_PIN,HIGH);
  pinMode(RST_PIN,OUTPUT);digitalWrite(RST_PIN,HIGH);pinMode(BUSY_PIN,INPUT);
  SPI.begin(SCK_PIN,MISO_PIN,MOSI_PIN,NSS_PIN);
  runDiagnostic();
}
void loop() {if(Serial.available()&&Serial.read()=='r')runDiagnostic();delay(10);}
