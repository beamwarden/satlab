# Wio Tracker L1 Cross-Link Setup

Hardware checklist for bringing up the Meshtastic cross-link between
beamrider-0003 and the second RPi node. Complete Phases 1–3 offline;
Phase 4 and 5 require both nodes powered and in range.

---

## Phase 1 — Initial connection and inspection

Both units ship pre-flashed with Meshtastic. Do this for each unit separately
using a laptop before touching the RPis.

**Easiest option — browser-based (no install required):**
- [ ] Connect Wio Tracker to laptop via USB-C
- [ ] Open Chrome or Edge (WebSerial is not supported in Firefox/Safari)
- [ ] Go to `client.meshtastic.org` → Connect → Serial → select the device port
- [ ] Confirm the Meshtastic UI loads and shows firmware version and node ID
      (displayed as `!xxxxxxxx` — record this for both units)
- [ ] Repeat for second unit

**Alternative — Python CLI:**
```bash
pip install meshtastic

# macOS — port appears as /dev/cu.usbmodem* (not ttyACM0)
meshtastic --port /dev/cu.usbmodem2101 --info

# Linux (RPi) — port appears as /dev/ttyACM0
meshtastic --port /dev/ttyACM0 --info
```
Look for `myInfo` → `myNodeNum` in the output. The node ID in `!xxxxxxxx`
format is the hex representation of that number.

> **macOS note:** Always use `/dev/cu.usbmodem*` for outgoing serial connections on macOS.
> `tty.usbmodem*` exists but hangs indefinitely. Run `ls /dev/cu.usbmodem*` to find the
> exact port name after plugging in the device.

> **PEP 668 note (macOS with Homebrew Python):** `pip install meshtastic` will
> refuse with "externally-managed-environment". Don't `--break-system-packages`
> against the system interpreter for a laptop-side CLI tool — use a throwaway
> venv instead: `python3 -m venv ~/.venvs/meshtastic-cli && ~/.venvs/meshtastic-cli/bin/pip install meshtastic`,
> then invoke as `~/.venvs/meshtastic-cli/bin/meshtastic ...`.

> **Board has a physical power switch.** Easy to miss: plugging in USB alone
> is not enough if the switch is off. No `/dev/cu.usbmodem*` device and an
> empty `system_profiler SPUSBDataType` (not even a hint of the accessory)
> means check the switch before suspecting the cable.

- [x] Connect Wio Tracker to laptop via USB-C -- **done 2026-08-23, via CLI**
- [x] Confirm firmware version and node ID
      -- Unit A: `!c107ec87` (firmware 2.7.15.567b8ea), Unit B: `!fe54bdf2`
      (firmware 2.6.10.9ce4455) -- **firmware versions differ slightly
      between the two units; config export/import and channel-URL sharing
      both worked fine across the gap, not observed to matter**
- [x] Repeat for second unit

---

## Phase 2 — Configure each Wio Tracker

Do for both units. The region and channel PSK must match for the two nodes
to communicate. Easiest to do one unit at a time on the laptop via CLI.

> **macOS port:** Use `/dev/cu.usbmodem*` (e.g. `/dev/cu.usbmodem2101`).
> Run `ls /dev/cu.usbmodem*` after plugging in to get the exact name.
> The commands below use `<PORT>` as a placeholder — substitute accordingly.

**Install CLI if not already done:**
```bash
pip install meshtastic
```

**Step 2a — Set region (required before the radio will transmit):**
```bash
meshtastic --port <PORT> --set lora.region US
```
The device will reboot. Wait ~5 s and reconnect for subsequent commands.

**Step 2b — Set LoRa preset:**
`LONG_FAST` is appropriate for indoor bench use (SF11, ~1 kbps, good
sensitivity). Matches the ≤1 kbps cross-link budget in the SBIR spec.
```bash
meshtastic --port <PORT> --set lora.modem_preset LONG_FAST
```

**Step 2c — Configure a private channel on Unit A:**
```bash
# Set channel name
meshtastic --port <PORT> --ch-index 0 --ch-set name satlab

# Generate a random PSK and apply it
meshtastic --port <PORT> --ch-index 0 --ch-set psk random
```

**Step 2d — DO NOT use `--export-config`/`--import-config` for this.** That was
the original plan here and it's wrong: a full config export includes the
`security` section (per-node PKI keypair), so importing it onto Unit B
**clones Unit A's device identity keys onto Unit B**. Both units then present
the same public key, and direct (non-broadcast) messages between them fail
with `PKI_UNKNOWN_PUBKEY` / `MAX_RETRANSMIT` even at zero range -- confirmed
2026-08-23, cost about 20 minutes to root-cause via the `--nodes` table
showing an identical `Pubkey` column for both units' self-entries.

Use the channel URL instead -- it carries only the channel name/PSK/LoRa
config, not device identity:
```bash
# On Unit A — set the channel, then grab its shareable URL
meshtastic --port <PORT> --ch-index 0 --ch-set name satlab
meshtastic --port <PORT> --ch-index 0 --ch-set psk random
meshtastic --port <PORT> --info   # "Primary channel URL:" line has the URL

# On Unit B — apply the same URL (sets channel + LoRa config, not identity)
meshtastic --port <PORT> --ch-set-url "<URL from Unit A>"
```
If Unit B already had a cloned identity from the old `--import-config`
approach, recover with `meshtastic --port <PORT> --factory-reset-device`
(wipes config *and* PKI keys, not just `--factory-reset`/`--factory-reset-config`
which explicitly preserves them) before reapplying region, channel URL, and
owner name.

**Step 2e — Set node names (do separately per unit):**
```bash
# Unit A
meshtastic --port <PORT> --set-owner "beamrider-0003" --set-owner-short "BR03"

# Unit B
meshtastic --port <PORT> --set-owner "beamrider-0004" --set-owner-short "BR04"
```

**Step 2f — Verify mesh connectivity before moving to the RPi:**
- [x] With both units powered (USB or battery), confirm Unit B appears in
      Unit A's node list -- **done 2026-08-23 via CLI (`--nodes`), not the
      browser UI. Took two tries: see the close-range note below.**
- [x] Send a test message to Unit B and confirm receipt -- **`--sendtext
      --dest !fe54bdf2 --ack` from Unit A got a real ACK; confirmed visually
      on both units' screens too**
- [x] Record both node IDs — Unit A (beamrider-0003) `!c107ec87`, Unit B
      (beamrider-0004) `!fe54bdf2`

> **Close-range gotcha:** the very first connectivity attempt (both units a
> few inches apart on the same desk, same USB hub) failed with
> `MAX_RETRANSMIT` and neither unit's `--nodes` table saw the other at all --
> this was on top of the PKI collision above, so two independent problems
> stacked. Moving the units a few feet apart and confirming both antennas
> were actually seated fixed the RF side; a LoRa front-end can desense at
> extreme close range the same way it can fail at extreme distance. If
> `--nodes` shows nothing after ~30s and both antennas are attached, try
> distance before assuming a config problem.

---

## Phase 3 — RPi software setup (both nodes)

- [ ] Install the Meshtastic Python library:
      `pip install meshtastic --break-system-packages`
- [ ] Plug the Wio Tracker into a USB port on the RPi
- [ ] Identify both USB serial devices with both Arduino and Wio Tracker plugged in:
      `ls /dev/serial/by-id/`
      This lists symlinks with stable, hardware-keyed names — use these instead
      of `/dev/ttyACM*` (which can swap order on reboot)
- [ ] Record the by-id path for the Arduino (will contain "Arduino" in the name)
      and for the Wio Tracker (will contain the nRF52840 USB descriptor)
- [ ] Update the systemd service environment to use by-id paths:
      `SATLAB_SERIAL_PORT=/dev/serial/by-id/usb-Arduino_LLC_Arduino_Uno_...-if00`
- [ ] Add the new cross-link environment variable to the service:
      `SATLAB_CROSSLINK_PORT=/dev/serial/by-id/usb-...<wio-tracker>...-if00`
- [ ] Add the peer node ID from Phase 2:
      `SATLAB_PEER_NODE_ID=!xxxxxxxx`
- [ ] Verify the Meshtastic Python library can reach the Wio Tracker:
      ```python
      import meshtastic.serial_interface
      iface = meshtastic.serial_interface.SerialInterface("/dev/serial/by-id/...")
      print(iface.myInfo)
      iface.close()
      ```
- [ ] Repeat on the second RPi node

---

## Phase 4 — Cross-link connectivity test (both nodes powered, in range)

**Done early, 2026-08-23, from the Mac via CLI rather than the RPis (Phase 3
hasn't happened yet -- both units were still on the laptop for Phase 1/2).
Re-verify after the physical move to the RPis in Phase 3; USB power/cabling
differences on the Pi are unlikely to matter but haven't been checked.**

- [x] Send a test message to the peer node ID -- `meshtastic --dest !fe54bdf2
      --sendtext ping --ack`, got a real ACK (see the PKI/close-range notes
      in Phase 2 for what it took to get here)
- [x] Confirm receipt on the peer -- confirmed visually on both units' screens
- [ ] Measure round-trip latency — expect 1–5 s at LongFast preset indoors
      (not measured precisely; CLI round trip felt sub-5s but wasn't timed)
- [x] Confirm bidirectional (send from B to A) -- ACK'd cleanly
- [x] Stress test: send 10 messages in succession, confirm delivery rate --
      **10/10 ACKed**

---

## Phase 5 — Agent integration smoke test

- [ ] Start the satlab agent on beamrider-0003 with the updated env vars
- [ ] Confirm Arduino telemetry still ingests to Beamwarden (no regression)
- [ ] Confirm health_vector readings appear in Beamwarden
- [ ] With `crosslink.py` integrated (software work, done separately):
      - [ ] Confirm health vectors appear in the agent log as transmitted
      - [ ] Confirm peer health vectors are received and logged on the other node
      - [ ] Confirm Beamwarden shows health_vector readings from both node IDs

---

## Environment variables added by this work

| Variable | Description |
|---|---|
| `SATLAB_CROSSLINK_PORT` | Serial device for Wio Tracker (use by-id path) |
| `SATLAB_PEER_NODE_ID` | Meshtastic node ID of the peer RPi node (e.g. `!a1b2c3d4`) |
| `SATLAB_NODE_ID` | Stable UUID for this node's health vector identity |

---

## Notes

**Packet size budget:** Meshtastic maximum payload is 237 bytes. The health
vector JSON payload (as currently structured) will exceed this at full
verbosity. Before `crosslink.py` is written, measure the serialized size
of `vector.to_payload()` and trim or compact if needed. The binary encoding
specified in the proposal (≤256 bytes) is the Phase II target; for the
Python prototype, compact JSON with short keys is a reasonable intermediate.

**USB port ordering (RPi/Linux):** Never rely on `/dev/ttyACM0` vs `/dev/ttyACM1` —
the kernel assigns these on plug-in order. Always use `/dev/serial/by-id/`
paths in env vars and the systemd service file.

**macOS serial port naming:** Use `/dev/cu.usbmodem*` for CLI commands, not
`/dev/tty.usbmodem*`. The `tty.*` variant hangs indefinitely when meshtastic
tries to open it. The CH340 driver (WCH `wch-ch34x-usb-serial-driver` cask)
is not needed for the nRF52840-based Wio Tracker L1 — it enumerates as a
native USB CDC device without additional drivers.

**Battery operation:** The 3000 mAh batteries allow the Wio Trackers to
operate untethered. For bench testing, USB power from the RPi is simpler.
Battery operation becomes relevant when testing cross-link range or
simulating ground contact blackouts.
