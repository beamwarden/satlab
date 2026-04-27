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
 *   D7  — DHT11/22 temp+humidity
 *   I2C — BMP280 air pressure (addr 0x76 or 0x77)
 *   I2C — MPU-6050 accelerometer (addr 0x68)
 *
 * Note: SSD1306 OLED omitted — Adafruit SSD1306+GFX libraries exceed the
 * Uno's 32KB flash when combined with dtostrf float support. Re-enable on
 * the Wio Tracker (nRF52840, 1MB flash) in iteration 2.
 *
 * Required libraries (install via Arduino Library Manager):
 *   Adafruit DHT sensor library + Adafruit Unified Sensor
 *   Adafruit BMP280
 *   Adafruit MPU6050 + Adafruit Unified Sensor
 */

#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// ── Pin config ───────────────────────────────────────────────────────────────
#define PIN_LIGHT       A0
#define PIN_SOUND       A1
#define PIN_DHT         7
#define DHT_TYPE        DHT11    // change to DHT22 if needed

// ── Timing ───────────────────────────────────────────────────────────────────
#define SAMPLE_INTERVAL_MS  10000UL   // 10 seconds

// ── Sensor objects ────────────────────────────────────────────────────────────
DHT             dht(PIN_DHT, DHT_TYPE);
Adafruit_BMP280 bmp;
Adafruit_MPU6050 mpu;

bool bmp_ok = false;
bool mpu_ok = false;

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
    dht.begin();

    bmp_ok = bmp.begin(0x76) || bmp.begin(0x77);
    mpu_ok = mpu.begin();

    // Emit sensor init status for RPi agent
    Serial.print("{\"ts\":");
    print_timestamp();
    Serial.print(",\"subsystem\":\"system\",\"sensor\":\"init\",\"payload\":{");
    Serial.print("\"bmp_ok\":");  Serial.print(bmp_ok ? "true" : "false");
    Serial.print(",\"mpu_ok\":"); Serial.print(mpu_ok ? "true" : "false");
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

    // ── TCS: temp + humidity ──────────────────────────────────────────────
    float humidity = dht.readHumidity();
    float temp_c   = dht.readTemperature();
    if (!isnan(humidity) && !isnan(temp_c)) {
        char st[10], sh[10];
        dtostrf(temp_c,   1, 2, st);
        dtostrf(humidity, 1, 2, sh);
        snprintf(buf, sizeof(buf), "{\"temp_c\":%s,\"humidity_pct\":%s}", st, sh);
        emit_packet("tcs", "dht", buf);
    }

    // ── Structural: air pressure ─────────────────────────────────────────
    if (bmp_ok) {
        float pressure_hpa = bmp.readPressure() / 100.0f;
        float bmp_temp     = bmp.readTemperature();
        char sp[10], sbt[10];
        dtostrf(pressure_hpa, 1, 2, sp);
        dtostrf(bmp_temp,     1, 2, sbt);
        snprintf(buf, sizeof(buf), "{\"pressure_hpa\":%s,\"temp_c\":%s}", sp, sbt);
        emit_packet("structural", "bmp280", buf);
    }

    // ── ADCS: accelerometer + gyro ───────────────────────────────────────
    if (mpu_ok) {
        sensors_event_t accel, gyro, temp_event;
        mpu.getEvent(&accel, &gyro, &temp_event);
        char sax[10], say[10], saz[10], sgx[10], sgy[10], sgz[10];
        dtostrf(accel.acceleration.x, 1, 3, sax);
        dtostrf(accel.acceleration.y, 1, 3, say);
        dtostrf(accel.acceleration.z, 1, 3, saz);
        dtostrf(gyro.gyro.x, 1, 3, sgx);
        dtostrf(gyro.gyro.y, 1, 3, sgy);
        dtostrf(gyro.gyro.z, 1, 3, sgz);
        snprintf(buf, sizeof(buf),
            "{\"ax_ms2\":%s,\"ay_ms2\":%s,\"az_ms2\":%s"
            ",\"gx_rads\":%s,\"gy_rads\":%s,\"gz_rads\":%s}",
            sax, say, saz, sgx, sgy, sgz);
        emit_packet("adcs", "mpu6050", buf);
    }
}
