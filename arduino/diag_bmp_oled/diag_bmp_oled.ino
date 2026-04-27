/*
 * satlab — BMP280 + OLED diagnostic
 *
 * Checks two things:
 *   1. BMP280 chip ID using a proper I2C repeated start (endTransmission(false))
 *      — the previous diagnostic likely sent a STOP, causing 0x0.
 *   2. Free SRAM before and after attempting OLED init — SSD1306 needs 1024 bytes
 *      of heap; the Uno only has 2048 bytes total.
 *
 * Upload standalone, open Serial Monitor at 9600 baud.
 * Expected output documented below each check.
 */

#include <Wire.h>
#include <Adafruit_SSD1306.h>

// ── SRAM diagnostic ──────────────────────────────────────────────────────────
extern int __heap_start, *__brkval;
static int freeRam() {
    int v;
    return (int)&v - (__brkval == 0 ? (int)&__heap_start : (int)__brkval);
}

// ── I2C register read with repeated start ────────────────────────────────────
static uint8_t i2cReadReg(uint8_t addr, uint8_t reg) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    // false = repeated start; do NOT release the bus before reading.
    // Using the default (true) sends a STOP, which causes many devices to
    // reset their internal register pointer and return 0x0 on the subsequent read.
    if (Wire.endTransmission(false) != 0) return 0xFE;  // TX error
    if (Wire.requestFrom(addr, (uint8_t)1) == 0) return 0xFF;  // no ACK
    return (uint8_t)Wire.read();
}

// ── OLED object (no-reset, -1 reset pin) ─────────────────────────────────────
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
    Serial.begin(9600);
    Wire.begin();
    delay(500);   // let sensors stabilize after power-on

    // ── I2C bus scan ─────────────────────────────────────────────────────────
    Serial.println(F("=== I2C bus scan ==="));
    for (uint8_t a = 1; a < 127; a++) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() == 0) {
            Serial.print(F("  found 0x")); Serial.println(a, HEX);
        }
    }

    // ── BMP280 chip ID — BOTH addresses, proper repeated start ───────────────
    Serial.println(F("\n=== BMP chip ID (repeated start) ==="));
    const uint8_t addrs[] = {0x76, 0x77};
    for (uint8_t i = 0; i < 2; i++) {
        uint8_t addr = addrs[i];
        uint8_t id   = i2cReadReg(addr, 0xD0);   // chip ID register
        Serial.print(F("  0x")); Serial.print(addr, HEX);
        Serial.print(F("  chip_id=0x")); Serial.print(id, HEX);
        if      (id == 0x60) Serial.print(F("  -> BMP280 or BME280 OK"));
        else if (id == 0x55) Serial.print(F("  -> BMP180 (different library needed)"));
        else if (id == 0x10) Serial.print(F("  -> DPS310 (different library needed)"));
        else if (id == 0x58) Serial.print(F("  -> BMP280 sample chip OK"));
        else if (id == 0xFE) Serial.print(F("  -> TX error (not present)"));
        else if (id == 0xFF) Serial.print(F("  -> no ACK on read"));
        else                 Serial.print(F("  -> unknown chip"));
        Serial.println();
    }

    // ── SRAM + OLED init ─────────────────────────────────────────────────────
    // SSD1306 128x64 needs malloc(1024). Uno has 2048 bytes SRAM total.
    // If free RAM < 1024, begin() will fail with no error message.
    Serial.println(F("\n=== OLED / SRAM ==="));
    Serial.print(F("  free RAM before begin: ")); Serial.println(freeRam());
    bool ok = display.begin(SSD1306_SWITCHCAPVCC, 0x3C, false);
    Serial.print(F("  begin() returned: ")); Serial.println(ok ? F("true") : F("false"));
    Serial.print(F("  free RAM after  begin: ")); Serial.println(freeRam());
    // If "free RAM before" < ~1100, malloc failed -> ok is false.
    // If "free RAM before" >= 1100 but ok is still false, it's a protocol issue.

    if (ok) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.print(F("diag ok"));
        display.display();
        Serial.println(F("  OLED rendered test string"));
    }

    Serial.println(F("\nDone."));
}

void loop() {}
