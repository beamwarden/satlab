# Ground Station Build — RTL-SDR Signal Reception

## Origin

`what.md` (the original project scoping document) listed an RTL-SDR dongle as an "Optional" radio component for "receiving simulated or real satellite signals," alongside a 433 MHz transmitter for outbound telemetry. Two Raspberry Pi 4s (2GB) and an RTL-SDR Blog V3 R860 dipole antenna kit were purchased against this line item, but the build went straight to USB-serial (Iteration 1) and then the Sense HAT node (beamrider-0004) instead — the ground station was never started. Flagged as a candidate next hardware build in the 2026-07 WORKLOG entry "satlab — RTL-SDR ground station intent surfaced."

This document did not exist before 2026-07-10; it's a synthesized plan, not a recovered one.

## Goal

Weekend build (2026-07-11/12), scoped to **box-to-first-signal-capture**: get the dongle, antenna, and a dedicated RPi 4 working as an independent RF receiver, with a real captured/decoded signal as proof of a working chain. This is a standalone RF capability, not yet wired into the Beamwarden ingest pipeline the way beamrider-0003/0004 are — see "Future integration" below for how it would eventually connect.

No CubeSatSim transmitter exists on the Arduino side (the 433 MHz TX half of the original scoping doc was never built), so receiving a simulated broadcast from satlab's own hardware isn't an option yet. The realistic weekend target is receiving a **real** signal — see Phase 2.

## Hardware

### On hand (per `~/git/corporate/hardware-inventory.md`)

| Item | Role |
|---|---|
| Raspberry Pi 4 (2GB) ×2 | One dedicated as the ground station host; second held as spare/second receiver |
| RTL-SDR Blog V3 (R860 tuner) | SDR (Software-Defined Radio) receiver dongle |
| Dipole antenna kit (telescoping elements) | Antenna, reconfigurable by element length for different bands |
| SenseCap Solar Node | Optional — outdoor RF source / power, not required for first light |

### Nothing to acquire — this build is fully funded by parts already on hand.

## Software setup

```bash
# 1. Flash Raspberry Pi OS Lite (64-bit) to the dedicated RPi 4 via Raspberry Pi Imager

# 2. Update and install RTL-SDR tools
sudo apt update && sudo apt install -y rtl-sdr gqrx-sdr rtl-433

# 3. Blacklist the DVB-T kernel driver (claims the dongle by default, conflicts with librtlsdr)
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo reboot

# 4. Verify the dongle is recognized and functional
rtl_test -t
```

## Build steps

### Phase 1 — Dongle/antenna sanity check (FM broadcast)

Cheapest way to confirm the whole chain (antenna → dongle → RPi → decode) works before pointing at anything satellite-related. Extend the dipole elements per the kit's FM-band length chart and tune to a known-strong local FM station:

```bash
rtl_fm -f 101.1M -M wbfm -s 200000 -r 48000 - | aplay -r 48000 -f S16_LE
```

Hearing clean audio confirms the receive chain end-to-end. If this doesn't work, nothing past it will either — debug here first.

### Phase 2 — Real satellite signal (NOAA APT, 137 MHz)

The standard, high-success-rate "first real satellite signal" project for this exact hardware class (RTL-SDR Blog V3 + dipole). NOAA 15/18/19 broadcast APT (Automatic Picture Transmission) continuously on 137 MHz — no ground-station coordination needed, just correct timing and antenna orientation during a pass.

```bash
# Install a decoder
sudo apt install -y noaa-apt

# Predict the next NOAA pass — satlab already has SGP4 + Space-Track wiring
# in agent/orbit.py; reuse those credentials rather than standing up a
# separate prediction tool if practical. gpredict is the standalone fallback:
sudo apt install -y gpredict
```

Re-extend the dipole elements to the ~137 MHz length (kit's length chart covers this band). During a pass (10-15 min window, check elevation — anything above ~20° is a reasonable first attempt), capture and decode:

```bash
rtl_fm -f 137.62M -s 60000 -g 40 -p 0 - | \
  sox -t raw -r 60000 -e signed -b 16 -c 1 - noaa_pass.wav
noaa-apt noaa_pass.wav -o noaa_image.png
```

A recognizable weather-satellite image out of `noaa_image.png` is the "first signal capture" success condition for this build.

## Future integration (not this weekend)

WORKLOG's original framing: this would "complete the satlab signal chain: Arduino sensors → flight computer → LoRa/RF → ground station → Beamwarden." Two integration paths exist once Phase 1/2 are working, neither in scope for this weekend:

- **Iteration 2 pairing** — once the Wio Tracker SX1262 LoRa link (Iteration 2, not yet built) is transmitting, this RPi/dongle could serve as an independent RF-layer receiver/monitor for it, separate from the Beamwarden ingest path.
- **Standalone Beamrider node** — register the ground-station RPi as its own Beamrider node in Beamwarden, ingesting signal-quality metrics (SNR, pass success/failure) as telemetry, analogous to beamrider-0003/0004.

## Reference

- rtl-sdr.com buying guide (original `what.md` reference): rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles
- CubeSatSim (original telemetry-sim reference, TX half never built): github.com/alanbjohnston/CubeSatSim
- noaa-apt decoder: github.com/martinber/noaa-apt
- gpredict: gpredict.oz9aec.net
- RTL-SDR Blog V3 quick-start guide: rtl-sdr.com/rtl-sdr-blog-v-3-dongles-user-guide
