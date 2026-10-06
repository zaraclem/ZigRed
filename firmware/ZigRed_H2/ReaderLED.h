#pragma once
#include <Preferences.h>

// Shared wire contract: version, brightness %, duration ms, then 8 states.
enum LedState { LED_IDLE, LED_AUTHORIZED, LED_DENIED, LED_UNKNOWN,
                LED_PENDING, LED_PAIRING, LED_ERROR, LED_OTA };
struct LedStyle { bool enabled, blink; uint32_t color; };
struct LedSettings { uint8_t brightness; uint16_t duration; LedStyle states[8]; };
static LedSettings ledSettings={15,2000,{
    {true,false,0x087ead},{true,false,0x00ff00},{true,false,0xff1493},{true,false,0xff0000},
    {true,true,0xffb000},{true,true,0xffb000},{true,true,0xff0000},{true,true,0xaa00ff}}};
static portMUX_TYPE ledMux=portMUX_INITIALIZER_UNLOCKED;
static char lastLedUid[23]={};
static uint32_t ledFeedbackAt=0;
static LedState ledVerdict=LED_PENDING;
static bool ledFeedbackValid=false, ledPersist=false;
static uint8_t ledConfigValue[73]={72}, ledFeedbackValue[40]={39};
static bool ledCapable=true;
static Preferences ledPrefs;

static bool parseHex(const char *text, size_t count, uint32_t &value) {
    value=0;
    for(size_t i=0;i<count;i++) {
        char c=text[i];uint8_t n;
        if(c>='0'&&c<='9')n=c-'0';else if(c>='A'&&c<='F')n=c-'A'+10;
        else if(c>='a'&&c<='f')n=c-'a'+10;else return false;
        value=(value<<4)|n;
    }
    return true;
}
static bool applyLedConfig(const char *text, size_t length, bool persist=true) {
    if(length!=72||text[0]!='0'||text[1]!='1')return false;
    uint32_t brightness,duration;
    if(!parseHex(text+2,2,brightness)||!parseHex(text+4,4,duration)||
       brightness<1||brightness>100||duration<500||duration>10000)return false;
    LedSettings next={static_cast<uint8_t>(brightness),static_cast<uint16_t>(duration),{}};
    for(size_t i=0;i<8;i++) {
        const char *p=text+8+i*8;uint32_t color;
        if((p[0]!='0'&&p[0]!='1')||(p[1]!='0'&&p[1]!='1')||!parseHex(p+2,6,color))return false;
        next.states[i]={p[0]=='1',p[1]=='1',color};
    }
    portENTER_CRITICAL(&ledMux);
    ledSettings=next;ledConfigValue[0]=72;memcpy(ledConfigValue+1,text,72);
    ledPersist=persist;
    portEXIT_CRITICAL(&ledMux);
    return true;
}
static void initializeLedSettings() {
    ledPrefs.begin("zigred-led",false);
    String saved=ledPrefs.getString("config","");
    if(!applyLedConfig(saved.c_str(),saved.length(),false)) {
        const char *defaults="010F07D010087EAD1000FF0010FF149310FF000011FFB00011FFB00011FF000011AA00FF";
        applyLedConfig(defaults,strlen(defaults),false);
    }
}
static void persistLedSettings() {
    char text[73];bool pending;
    portENTER_CRITICAL(&ledMux);
    pending=ledPersist;ledPersist=false;
    memcpy(text,ledConfigValue+1,72);text[72]=0;
    portEXIT_CRITICAL(&ledMux);
    if(pending)ledPrefs.putString("config",text);
}
static void ledBadgeRead(const String &uid) {
    portENTER_CRITICAL(&ledMux);
    if(strcmp(lastLedUid,uid.c_str())!=0||uint32_t(millis()-badgeSeen)>3000)ledFeedbackValid=false;
    strlcpy(lastLedUid,uid.c_str(),sizeof(lastLedUid));badgeSeen=millis();
    portEXIT_CRITICAL(&ledMux);
}
static void applyLedFeedback(const char *text, size_t length) {
    if(length>=40)return;
    char packet[40];memcpy(packet,text,length);packet[length]=0;
    char *separator=strchr(packet,'|');if(!separator)return;*separator++=0;
    LedState state;
    if(strcmp(separator,"authorized")==0)state=LED_AUTHORIZED;
    else if(strcmp(separator,"denied")==0)state=LED_DENIED;
    else if(strcmp(separator,"unknown")==0)state=LED_UNKNOWN;else return;
    portENTER_CRITICAL(&ledMux);
    if(strcmp(lastLedUid,packet)==0&&badgeSeen&&uint32_t(millis()-badgeSeen)<3000) {
        ledVerdict=state;ledFeedbackAt=millis();ledFeedbackValid=true;
    }
    portEXIT_CRITICAL(&ledMux);
}
static uint32_t currentLedColor(uint32_t now, bool stalled) {
    LedSettings settings;LedState state;bool valid;uint32_t feedback;
    portENTER_CRITICAL(&ledMux);
    settings=ledSettings;state=ledVerdict;valid=ledFeedbackValid;feedback=ledFeedbackAt;
    portEXIT_CRITICAL(&ledMux);
    if(otaRunning)state=LED_OTA;
    else if(startupFault||nfcFault||stalled||(reportFailed&&uint32_t(now-reportFailed)<1500))state=LED_ERROR;
    else if(!zigbeeOnline)state=LED_PAIRING;
    else if(valid&&uint32_t(now-feedback)<settings.duration){} // HA verdict only
    else if(badgeSeen&&uint32_t(now-badgeSeen)<1300)state=LED_PENDING;
    else state=LED_IDLE;
    LedStyle style=settings.states[state];
    if(!style.enabled||(style.blink&&(now/400)%2==0))return 0;
    uint8_t r=((style.color>>16)&255)*settings.brightness/100;
    uint8_t g=((style.color>>8)&255)*settings.brightness/100;
    uint8_t b=(style.color&255)*settings.brightness/100;
    return (uint32_t(r)<<16)|(uint32_t(g)<<8)|b;
}
