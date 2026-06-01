/*
 * satlab — Subsystem Simulator
 *
 * Reads all sensors every SAMPLE_INTERVAL_MS and emits one newline-delimited
 * JSON packet per sensor over Serial at 9600 baud.
 *
 * 9600 baud matches realistic spacecraft UART housekeeping rates and is
 * consistent with the ≤1 kbps cross-link budget in the SBIR architecture.
 * The Wio Tracker SX1262 LoRa link (iteration 2) will operate near this
 * rate — designing to it now prevents format rework at radio integration.
 *
 * Packet format:
 *   {"ts":"<ISO8601>","subsystem":"<name>","sensor":"<name>","payload":{...}}
 *
 * Pin assignments (adjust to match your wiring):
 *   A0  — LDR light sensor (analog)
 *   A1  — Sound / microphone sensor (analog)
 *   I2C — AHT20 temp+humidity (addr 0x38)
 *   I2C — DPS310 air pressure (addr 0x77, chip_id reg[0x0D]=0x11, rev 1)
 *   I2C — LIS3DHTR accelerometer (addr 0x19)
 *
 * Required libraries (install via arduino-cli lib install):
 *   Adafruit AHTX0
 *   Adafruit DPS310  — patch required: Adafruit_DPS310.cpp line 134,
 *                      change (chip_id.read() != 0x10) to
 *                      ((chip_id.read() & 0xF0) != 0x10) to accept rev 0x11
 *   Seeed Arduino LIS3DHTR
 *
 * OLED deferred to iteration 2 (Wio Tracker, nRF52840, 256 KB RAM).
 * Uno has only 988 bytes of heap available with this sensor suite loaded;
 * the SSD1306 128x64 frame buffer requires 1024 bytes.
 */

#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include "Adafruit_DPS310.h"
#include "LIS3DHTR.h"

// ── Pin config ───────────────────────────────────────────────────────────────
#define PIN_LIGHT       A0
#define PIN_SOUND       A1

// ── Timing ───────────────────────────────────────────────────────────────────
#define SAMPLE_INTERVAL_MS  10000UL   // 10 seconds

// ── Sensor objects ────────────────────────────────────────────────────────────
Adafruit_AHTX0    aht;
Adafruit_DPS310   dps;
LIS3DHTR<TwoWire> lis;

bool aht_ok  = false;
bool dps_ok  = false;
bool lis_ok  = false;

unsigned long last_sample = 0;

// ── Helpers ───────────────────────────────────────────────────────────────────

// Arduino has no RTC — emit elapsed seconds since boot as a placeholder.
// RPi agent replaces this with wall-clock UTC.
void print_timestamp() {
    unsigned long s = millis() / 1000UL;
    Serial.print("\"T+");
    Serial.print(s);
    Serial.print("s\"");
}

void emit_packet(const char* subsystem, const char* sensor, const char* payload_json) {
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"");
    Serial.print(subsystem);
    Serial.print("\",\"sensor\":\"");
    Serial.print(sensor);
    Serial.print("\",\"payload\":");
    Serial.print(payload_json);
    Serial.println("}");
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);
    while (!Serial) {}

    Wire.begin();
    delay(100);

    aht_ok  = aht.begin();
    dps_ok  = dps.begin_I2C(0x77);
    lis.begin(Wire, 0x19);
    lis_ok  = lis.available();
    if (lis_ok) {
        lis.setOutputDataRate(LIS3DHTR_DATARATE_100HZ);
        lis.setFullScaleRange(LIS3DHTR_RANGE_2G);
        lis.setHighSolution(true);
    }

    // Emit sensor init status for RPi agent
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"system\",\"sensor\":\"init\",\"payload\":{");
    Serial.print("\"aht_ok\":");  Serial.print(aht_ok  ? "true" : "false");
    Serial.print(",\"dps_ok\":"); Serial.print(dps_ok  ? "true" : "false");
    Serial.print(",\"lis_ok\":"); Serial.print(lis_ok  ? "true" : "false");
    Serial.println("}}");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();
    if (now - last_sample < SAMPLE_INTERVAL_MS) return;
    last_sample = now;

    char buf[128];

    // ── EPS: light (solar panel / illumination analog) ────────────────────
    int light_raw = analogRead(PIN_LIGHT);
    int light_pct = (int)((light_raw * 100L) / 1023);
    snprintf(buf, sizeof(buf), "{\"raw\":%d,\"pct\":%d}", light_raw, light_pct);
    emit_packet("eps", "light", buf);

    // ── Structural: sound (microphone — vibration / structural health) ────
    int sound_raw = analogRead(PIN_SOUND);
    snprintf(buf, sizeof(buf), "{\"raw\":%d}", sound_raw);
    emit_packet("structural", "sound", buf);

    // ── TCS: temp + humidity (AHT20, I2C 0x38) ───────────────────────────
    float temp_c = 0, humidity = 0;
    if (aht_ok) {
        sensors_event_t humidity_ev, temp_ev;
        aht.getEvent(&humidity_ev, &temp_ev);
        temp_c   = temp_ev.temperature;
        humidity = humidity_ev.relative_humidity;
        char st[10], sh[10];
        dtostrf(temp_c,   1, 2, st);
        dtostrf(humidity, 1, 2, sh);
        snprintf(buf, sizeof(buf), "{\"temp_c\":%s,\"humidity_pct\":%s}", st, sh);
        emit_packet("tcs", "dht", buf);
    }

    // ── Structural: air pressure (DPS310, I2C 0x77) ──────────────────────
    float pressure_hpa = 0;
    if (dps_ok) {
        sensors_event_t temp_ev, pressure_ev;
        dps.getEvents(&temp_ev, &pressure_ev);
        pressure_hpa      = pressure_ev.pressure;
        float dps_temp    = temp_ev.temperature;
        char sp[10], sbt[10];
        dtostrf(pressure_hpa, 1, 2, sp);
        dtostrf(dps_temp,     1, 2, sbt);
        snprintf(buf, sizeof(buf), "{\"pressure_hpa\":%s,\"temp_c\":%s}", sp, sbt);
        emit_packet("structural", "bmp280", buf);   // sensor name unchanged in Beamwarden
    }

    // ── ADCS: LIS3DHTR 3-axis accelerometer ─────────────────────────────
    if (lis_ok) {
        float ax = lis.getAccelerationX();
        float ay = lis.getAccelerationY();
        float az = lis.getAccelerationZ();
        char sax[12], say[12], saz[12];
        dtostrf(ax, 1, 4, sax);
        dtostrf(ay, 1, 4, say);
        dtostrf(az, 1, 4, saz);
        snprintf(buf, sizeof(buf), "{\"ax_g\":%s,\"ay_g\":%s,\"az_g\":%s}", sax, say, saz);
        emit_packet("adcs", "lis3dh", buf);
    }
}
