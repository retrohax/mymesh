// Meshtastic LoRa Promiscuous Sniffer
// For Heltec WiFi LoRa 32 V3 (SX1262 + ESP32-S3)
//
// Listens promiscuously on the Meshtastic LONG_FAST US channel and streams
// raw LoRa frames to the host over USB serial at 921600 baud.
//
// Frame format (binary):
//   "PKT"        - 3-byte magic
//   length       - 2 bytes, big-endian, number of LoRa payload bytes
//   payload      - <length> bytes of raw LoRa data (PacketHeader + encrypted Data)
//   rssi         - 4 bytes, little-endian float, RSSI in dBm
//   snr          - 4 bytes, little-endian float, SNR in dB
//
// Heltec V3 SX1262 wiring:
//   NSS  -> GPIO 8    DIO1 -> GPIO 14
//   RST  -> GPIO 12   BUSY -> GPIO 13
//   MOSI -> GPIO 10   MISO -> GPIO 11   SCK -> GPIO 9

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>

// Use FSPI bus with explicit Heltec V3 pin assignments
SPIClass radioSPI(FSPI);

// NSS=8, DIO1=14, RST=12, BUSY=13
SX1262 radio = new Module(8, 14, 12, 13, radioSPI);

volatile bool receivedFlag = false;

void IRAM_ATTR setFlag(void) {
    receivedFlag = true;
}

void setup() {
    Serial.begin(921600);

    // Init SPI: SCK=9, MISO=11, MOSI=10, SS=8
    radioSPI.begin(9, 11, 10, 8);

    // Match Meshtastic LONG_FAST US settings exactly:
    //   freq=906.875 MHz, BW=250 kHz, SF=11, CR=4/8,
    //   syncWord=0x2B, preamble=16, TCXO=1.8V
    int state = radio.begin(906.875, 250.0, 11, 8, 0x2b, 22, 16, 1.8, false);
    if (state != RADIOLIB_ERR_NONE) {
        // Nothing to do but hang — no OLED/LED driver included here
        while (true) { delay(1000); }
    }

    // CRC enabled by default in RadioLib (matches Meshtastic); keep it.
    // Only packets with valid CRC are delivered; payload does NOT include CRC bytes.

    radio.setDio1Action(setFlag);
    radio.startReceive();
}

void loop() {
    if (!receivedFlag) return;
    receivedFlag = false;

    int len = radio.getPacketLength();
    if (len > 0 && len <= 256) {
        uint8_t buf[256];
        int state = radio.readData(buf, len);
        if (state == RADIOLIB_ERR_NONE) {
            float rssi = radio.getRSSI();
            float snr  = radio.getSNR();

            // Write framing magic
            Serial.write((const uint8_t *)"PKT", 3);
            // 2-byte big-endian length
            Serial.write((uint8_t)(len >> 8));
            Serial.write((uint8_t)(len & 0xFF));
            // Raw payload
            Serial.write(buf, len);
            // RSSI and SNR as little-endian floats (native ESP32 byte order)
            Serial.write((const uint8_t *)&rssi, 4);
            Serial.write((const uint8_t *)&snr,  4);
            Serial.flush();
        }
    }

    radio.startReceive();
}
