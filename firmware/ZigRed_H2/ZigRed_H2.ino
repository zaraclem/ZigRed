// ESP32-H2 / PN5180, Arduino-ESP32 3.3.2, router with 4 MB OTA partitions.
#include <Arduino.h>
#include <SPI.h>
#include <PN5180ISO14443.h>
#include <PN5180ISO15693.h>
#include "Zigbee.h"
#include "esp_zigbee_cluster.h"
#include "version.h"
#ifndef ZIGBEE_MODE_ZCZR
#error Select Zigbee ZCZR and Zigbee ZCZR 4MB partitions.
#endif
constexpr int PIN_SCK=4, PIN_MOSI=5, PIN_MISO=0, PIN_NSS=1, PIN_BUSY=10, PIN_RST=11;
constexpr uint8_t ENDPOINT=1;
constexpr uint16_t CLUSTER=0xFF00;
constexpr uint32_t REPORT_MS=900;
PN5180ISO14443 readerA(PIN_NSS,PIN_BUSY,PIN_RST);
PN5180ISO15693 readerV(PIN_NSS,PIN_BUSY,PIN_RST);
volatile bool otaRunning=false;
// ESP32-H2 DevKitM-1: addressable RGB LED on GPIO8, independent of NFC SPI.
constexpr uint8_t STATUS_LED_PIN=8;
volatile bool nfcReady=false, nfcBusy=false, nfcFault=false, startupFault=false, zigbeeOnline=false;
volatile uint32_t nfcStarted=0, badgeSeen=0, reportFailed=0;
#include "ReaderLED.h"
static void statusLedTask(void *) {
    uint32_t previous=0xffffffff; bool warned=false;
    for(;;) {
        uint32_t now=millis();
        bool stalled=nfcBusy && uint32_t(now-nfcStarted)>2000;
        uint32_t color=currentLedColor(now,stalled);
        if(color!=previous){rgbLedWrite(STATUS_LED_PIN,(color>>16)&255,(color>>8)&255,color&255);previous=color;}
        if(stalled && !warned){Serial.println("PN5180 operation exceeds 2 s; inspect the preceding diagnostic stage");warned=true;}
        if(!stalled)warned=false;
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
static uint8_t tagValue[23]={0};
static uint32_t firmwareVersion=ZIGRED_FILE_VERSION;
static bool otaCapable=true;
class ZigRedEndpoint : public ZigbeeEP {
public:
    ZigRedEndpoint() : ZigbeeEP(ENDPOINT) {
        _device_id=ESP_ZB_HA_CUSTOM_ATTR_DEVICE_ID;
        _ep_config={};
        _ep_config.endpoint=ENDPOINT;
        _ep_config.app_profile_id=ESP_ZB_AF_HA_PROFILE_ID;
        _ep_config.app_device_id=_device_id;
        _cluster_list=esp_zb_zcl_cluster_list_create();
        esp_zb_cluster_list_add_basic_cluster(_cluster_list,esp_zb_basic_cluster_create(NULL),ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);
        esp_zb_cluster_list_add_identify_cluster(_cluster_list,esp_zb_identify_cluster_create(NULL),ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);
        auto custom=esp_zb_zcl_attr_list_create(CLUSTER);
        ESP_ERROR_CHECK(esp_zb_custom_cluster_add_custom_attr(custom,0,ESP_ZB_ZCL_ATTR_TYPE_CHAR_STRING,
            ESP_ZB_ZCL_ATTR_ACCESS_READ_ONLY|ESP_ZB_ZCL_ATTR_ACCESS_REPORTING,tagValue));
        ESP_ERROR_CHECK(esp_zb_custom_cluster_add_custom_attr(custom,1,ESP_ZB_ZCL_ATTR_TYPE_U32,
            ESP_ZB_ZCL_ATTR_ACCESS_READ_ONLY|ESP_ZB_ZCL_ATTR_ACCESS_REPORTING,&firmwareVersion));
        ESP_ERROR_CHECK(esp_zb_custom_cluster_add_custom_attr(custom,2,ESP_ZB_ZCL_ATTR_TYPE_BOOL,
            ESP_ZB_ZCL_ATTR_ACCESS_READ_ONLY,&otaCapable));
        ESP_ERROR_CHECK(esp_zb_custom_cluster_add_custom_attr(custom,3,ESP_ZB_ZCL_ATTR_TYPE_CHAR_STRING,
            ESP_ZB_ZCL_ATTR_ACCESS_READ_WRITE|ESP_ZB_ZCL_ATTR_ACCESS_REPORTING,ledConfigValue));
        ESP_ERROR_CHECK(esp_zb_custom_cluster_add_custom_attr(custom,4,ESP_ZB_ZCL_ATTR_TYPE_CHAR_STRING,
            ESP_ZB_ZCL_ATTR_ACCESS_WRITE_ONLY,ledFeedbackValue));
        ESP_ERROR_CHECK(esp_zb_custom_cluster_add_custom_attr(custom,5,ESP_ZB_ZCL_ATTR_TYPE_BOOL,
            ESP_ZB_ZCL_ATTR_ACCESS_READ_ONLY,&ledCapable));
        ESP_ERROR_CHECK(esp_zb_cluster_list_add_custom_cluster(_cluster_list,custom,ESP_ZB_ZCL_CLUSTER_SERVER_ROLE));
    }
    void zbAttributeSet(const esp_zb_zcl_set_attr_value_message_t *message) override {
        if(message->info.cluster!=CLUSTER||message->attribute.data.type!=ESP_ZB_ZCL_ATTR_TYPE_CHAR_STRING||
           !message->attribute.data.value)return;
        const uint8_t *value=static_cast<const uint8_t *>(message->attribute.data.value);
        if(message->attribute.id==3)applyLedConfig(reinterpret_cast<const char *>(value+1),value[0]);
        else if(message->attribute.id==4)applyLedFeedback(reinterpret_cast<const char *>(value+1),value[0]);
    }
};
ZigRedEndpoint reader;
static bool reportAttribute(uint16_t attribute) {
    esp_zb_zcl_report_attr_cmd_t cmd={};
    cmd.zcl_basic_cmd.dst_addr_u.addr_short=0;
    cmd.zcl_basic_cmd.src_endpoint=ENDPOINT;cmd.zcl_basic_cmd.dst_endpoint=1;
    cmd.address_mode=ESP_ZB_APS_ADDR_MODE_16_ENDP_PRESENT;
    cmd.direction=ESP_ZB_ZCL_CMD_DIRECTION_TO_CLI;cmd.clusterID=CLUSTER;cmd.attributeID=attribute;
    return esp_zb_zcl_report_attr_cmd_req(&cmd)==ESP_OK;
}
static bool sendUid(const String &uid) {
    if(!Zigbee.connected()||otaRunning||uid.length()>sizeof(tagValue)-1)return false;
    uint8_t value[sizeof(tagValue)]={0};value[0]=static_cast<uint8_t>(uid.length());
    memcpy(value+1,uid.c_str(),uid.length());
    if(!esp_zb_lock_acquire(pdMS_TO_TICKS(1000)))return false;
    auto result=esp_zb_zcl_set_attribute_val(ENDPOINT,CLUSTER,ESP_ZB_ZCL_CLUSTER_SERVER_ROLE,0,value,false);
    bool sent=result==ESP_ZB_ZCL_STATUS_SUCCESS&&reportAttribute(0);
    esp_zb_lock_release();return sent;
}
static String hexUid(const char *prefix,const uint8_t *bytes,uint8_t length) {
    String result(prefix);
    for(uint8_t i=0;i<length;++i){char pair[3];snprintf(pair,sizeof(pair),"%02X",bytes[i]);result+=pair;}
    return result;
}
static bool prepareRF(PN5180 &nfc, uint8_t tx, uint8_t rx) {
    // Stop the preceding transceive and turn the field off before changing protocol.
    if(!nfc.writeRegisterWithAndMask(SYSTEM_CONFIG,0xfffffff8))return false;
    uint32_t rf=0;
    if(!nfc.readRegister(RF_STATUS,&rf))return false;
    if((rf&(1UL<<17))&&!nfc.setRF_off())return false;
    if(!nfc.clearIRQStatus(0x000fffff))return false;
    if(!nfc.writeRegisterWithOrMask(IRQ_ENABLE,0x0001ffff))return false;
    if(!nfc.loadRFConfig(tx,rx))return false;
    uint32_t irq=0;
    if(!nfc.readRegister(IRQ_STATUS,&irq))return false;
    if(irq&(1UL<<17)){
        uint32_t system=0;nfc.readRegister(SYSTEM_STATUS,&system);
        Serial.printf("PN5180 LOAD_RF_CONFIG rejected: tx=0x%02X rx=0x%02X IRQ=0x%08lX SYSTEM=0x%08lX\n",tx,rx,(unsigned long)irq,(unsigned long)system);
        nfcReady=false;nfcFault=true;return false;
    }
    return nfc.setRF_on();
}
static bool finishRF(PN5180 &nfc) {
    if(!nfc.writeRegisterWithAndMask(SYSTEM_CONFIG,0xfffffff8))return false;
    return nfc.setRF_off();
}
static String readTag() {
    uint8_t uidA[10]={};
    if(!prepareRF(readerA,0x00,0x80))return {};
    uint8_t n=readerA.readCardSerial(uidA);
    if(readerA.hasTransportError()||!finishRF(readerA))return {};
    if(n==4||n==7)return hexUid("A:",uidA,n);
    uint8_t uidV[8]={};
    if(!prepareRF(readerV,0x0d,0x8d))return {};
    if(!readerV.writeRegisterWithAndMask(SYSTEM_CONFIG,0xfffffff8)||
       !readerV.writeRegisterWithOrMask(SYSTEM_CONFIG,0x00000003))return {};
    auto result=readerV.getInventory(uidV);
    if(readerV.hasTransportError()||!finishRF(readerV))return {};
    if(result==ISO15693_EC_OK){
        uint8_t canonical[8];for(uint8_t i=0;i<8;++i)canonical[i]=uidV[7-i];return hexUid("V:",canonical,8);
    }
    return {};
}
static void initializeNFC() {
    nfcStarted=millis();nfcBusy=true;
    Serial.println("PN5180 stage: initialize SPI (1 MHz)");
    SPI.begin(PIN_SCK,PIN_MISO,PIN_MOSI,PIN_NSS);
    readerA.begin();readerV.begin();
    Serial.printf("PN5180 stage: reset; BUSY=%d\n",digitalRead(PIN_BUSY));
    readerA.reset();
    uint8_t pnVersion[2]={};
    bool versionRead=false;
    if(!readerA.hasTransportError()){
        Serial.println("PN5180 stage: read firmware EEPROM");
        versionRead=readerA.readEEprom(0x12,pnVersion,2);
    }
    nfcReady=versionRead && !((pnVersion[0]==0 && pnVersion[1]==0)||(pnVersion[0]==0xff && pnVersion[1]==0xff));
    if(nfcReady){
        // IRQ flags awaited by the driver must be enabled explicitly.
        nfcReady=readerA.writeRegisterWithOrMask(IRQ_ENABLE,0x0001ffff)&&readerA.clearIRQStatus(0x000fffff);
        uint32_t enabled=0,system=0;
        if(nfcReady)nfcReady=readerA.readRegister(IRQ_ENABLE,&enabled)&&readerA.readRegister(SYSTEM_STATUS,&system);
        Serial.printf("PN5180 startup: IRQ_ENABLE=0x%08lX SYSTEM=0x%08lX\n",(unsigned long)enabled,(unsigned long)system);
    }
    nfcBusy=false;
    nfcFault=!nfcReady;
    Serial.printf("PN5180 firmware: %u.%u (%s)\n",pnVersion[1],pnVersion[0],nfcReady?"SPI response OK":"initialization failed; retry in 10 s");
}
void setup() {
    Serial.begin(115200);delay(300);Serial.printf("ZigRed %s\n",ZIGRED_VERSION);
    initializeLedSettings();
    if(xTaskCreate(statusLedTask,"zigred-led",4096,nullptr,1,nullptr)!=pdPASS)Serial.println("RGB status task unavailable");
    Serial.printf("PN5180 pins: SCK=%d MOSI=%d MISO=%d NSS=%d BUSY=%d RST=%d\n",PIN_SCK,PIN_MOSI,PIN_MISO,PIN_NSS,PIN_BUSY,PIN_RST);
    initializeNFC();
    reader.setManufacturerAndModel("DIY","ZigRed-H2");reader.setPowerSource(ZB_POWER_SOURCE_MAINS);
    if(!reader.addOTAClient(ZIGRED_FILE_VERSION,0,ZIGRED_HW_VERSION,ZIGRED_MANUFACTURER,ZIGRED_IMAGE_TYPE)){
        startupFault=true;Serial.println("OTA initialization failed");return;
    }
    reader.onOTAStateChange([](bool active){otaRunning=active;Serial.println(active?"OTA started":"OTA completed or stopped");});
    Zigbee.addEndpoint(&reader);
    if(!Zigbee.begin(ZIGBEE_ROUTER)){startupFault=true;Serial.println("Zigbee initialization failed");}
}
void loop() {
    static String lastUid;static uint32_t lastReport=0,lastVersionReport=0,lastNfcRetry=0;static bool wasConnected=false;
    zigbeeOnline=Zigbee.connected();
    persistLedSettings();
    if(!nfcReady&&!otaRunning&&millis()-lastNfcRetry>=10000){
        lastNfcRetry=millis();initializeNFC();
    }
    if(!zigbeeOnline||otaRunning){wasConnected=false;delay(100);return;}
    if(!wasConnected){Serial.println("Zigbee connected");reader.requestOTAUpdate();wasConnected=true;}
    if(millis()-lastVersionReport>60000||lastVersionReport==0){
        esp_zb_lock_acquire(portMAX_DELAY);reportAttribute(1);esp_zb_lock_release();lastVersionReport=millis();
    }
    if(!nfcReady){delay(100);return;}
    nfcStarted=millis();nfcBusy=true;
    String uid=readTag();
    nfcBusy=false;
    if(readerA.hasTransportError()||readerV.hasTransportError()){
        nfcReady=false;nfcFault=true;
        Serial.println("PN5180 transport failed during badge polling; retry in 10 s");
        delay(100);return;
    }
    if(!uid.isEmpty())ledBadgeRead(uid);
    if(!uid.isEmpty()&&(uid!=lastUid||millis()-lastReport>=REPORT_MS)){
        bool sent=sendUid(uid);
        if(uid!=lastUid || !sent)Serial.printf("NFC UID %s; Zigbee report %s\n",uid.c_str(),sent?"queued":"FAILED");
        if(sent){lastUid=uid;lastReport=millis();}else reportFailed=millis();
    }
    if(uid.isEmpty())lastUid="";delay(110);
}
