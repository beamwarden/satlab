from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from datetime import datetime, timezone

import serial

logger = logging.getLogger(__name__)

_RECONNECT_DELAY_S = 3


def _replace_arduino_timestamp(packet: dict, wall_clock: datetime) -> dict:
    """
    Arduino has no RTC — it emits elapsed boot time as the 'ts' field.
    Replace it with the RPi's wall-clock UTC before forwarding to Beamwarden.
    """
    packet["ts"] = wall_clock.isoformat()
    return packet


def read_packets(port: str, baud: int = 9600) -> Iterator[dict]:
    """
    Open a serial port and yield parsed JSON packets indefinitely.

    Reconnects automatically if the device resets or is power-cycled.
    Each Arduino line is expected to be a complete JSON object terminated by
    a newline. Malformed lines are logged and skipped.
    """
    logger.info("opening serial port %s at %d baud", port, baud)
    while True:
        try:
            with serial.Serial(port, baud, timeout=30) as ser:
                logger.info("serial port open")
                while True:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        packet = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("non-JSON line: %s", line[:120])
                        continue
                    yield _replace_arduino_timestamp(packet, datetime.now(timezone.utc))
        except serial.SerialException as exc:
            logger.warning("serial port disconnected: %s — reconnecting in %ds",
                           exc, _RECONNECT_DELAY_S)
            time.sleep(_RECONNECT_DELAY_S)
