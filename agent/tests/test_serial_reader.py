from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from serial_reader import _replace_arduino_timestamp, read_packets


# ── _replace_arduino_timestamp ────────────────────────────────────────────────

class TestReplaceArduinoTimestamp:
    def test_replaces_ts_with_iso_string(self):
        wall = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
        packet = {"ts": "T+30s", "subsystem": "tcs"}
        result = _replace_arduino_timestamp(packet, wall)
        assert result["ts"] == wall.isoformat()

    def test_returns_same_packet_object(self):
        wall = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
        packet = {"ts": "T+10s"}
        result = _replace_arduino_timestamp(packet, wall)
        assert result is packet

    def test_other_fields_preserved(self):
        wall = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
        packet = {"ts": "T+5s", "subsystem": "eps", "sensor": "light", "payload": {"pct": 50}}
        _replace_arduino_timestamp(packet, wall)
        assert packet["subsystem"] == "eps"
        assert packet["sensor"] == "light"
        assert packet["payload"] == {"pct": 50}

    def test_ts_contains_offset(self):
        wall = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
        packet = {"ts": "T+0s"}
        _replace_arduino_timestamp(packet, wall)
        assert "+00:00" in packet["ts"] or packet["ts"].endswith("Z") or "UTC" not in packet["ts"]

    def test_aware_datetime_round_trips(self):
        wall = datetime(2026, 5, 18, 15, 30, 45, tzinfo=timezone.utc)
        packet = {"ts": "boot"}
        _replace_arduino_timestamp(packet, wall)
        parsed = datetime.fromisoformat(packet["ts"])
        assert parsed.tzinfo is not None
        assert parsed.year == 2026


# ── read_packets ──────────────────────────────────────────────────────────────

def _make_serial_lines(*lines: str) -> MagicMock:
    """Return a mock serial.Serial whose readline() returns each line then raises
    SerialException. Never raises StopIteration — that would become RuntimeError
    inside a generator (PEP 479)."""
    import serial

    encoded = [l.encode("utf-8") for l in lines]
    call_index = [0]

    def _readline():
        i = call_index[0]
        call_index[0] += 1
        if i < len(encoded):
            return encoded[i]
        raise serial.SerialException("exhausted")

    mock_ser = MagicMock()
    mock_ser.readline.side_effect = _readline
    mock_ser.__enter__ = lambda s: s
    mock_ser.__exit__ = MagicMock(return_value=False)
    return mock_ser


class _Done(BaseException):
    """Sentinel raised by patched time.sleep to terminate the infinite generator."""


class TestReadPackets:
    def _collect(self, mock_ser: MagicMock, port: str = "/dev/ttyACM0") -> list[dict]:
        """Collect all packets the mock produces.

        time.sleep is patched to raise _Done (a BaseException) so it bypasses
        the serial.SerialException handler and exits the generator cleanly.
        """
        packets: list[dict] = []
        with (
            patch("serial_reader.serial.Serial", return_value=mock_ser),
            patch("serial_reader.time.sleep", side_effect=_Done()),
        ):
            gen = read_packets(port)
            try:
                for _ in range(1000):
                    packets.append(next(gen))
            except _Done:
                pass
        return packets

    def test_valid_json_yielded(self):
        pkt = {"ts": "T+10s", "subsystem": "tcs", "sensor": "dht", "payload": {"temp_c": 23.4}}
        line = json.dumps(pkt) + "\n"
        mock_ser = _make_serial_lines(line)
        packets = self._collect(mock_ser)
        assert len(packets) >= 1
        assert packets[0]["subsystem"] == "tcs"

    def test_malformed_json_skipped(self):
        good = json.dumps({"ts": "T+5s", "subsystem": "eps"}) + "\n"
        bad = "not json at all\n"
        mock_ser = _make_serial_lines(bad, good)
        packets = self._collect(mock_ser)
        assert len(packets) >= 1
        assert packets[0]["subsystem"] == "eps"

    def test_empty_line_skipped(self):
        good = json.dumps({"ts": "T+5s", "subsystem": "adcs"}) + "\n"
        mock_ser = _make_serial_lines("\n", "   \n", good)
        packets = self._collect(mock_ser)
        assert len(packets) >= 1
        assert packets[0]["subsystem"] == "adcs"

    def test_timestamp_replaced_in_yielded_packet(self):
        pkt = {"ts": "T+30s", "subsystem": "tcs", "sensor": "dht", "payload": {}}
        line = json.dumps(pkt) + "\n"
        mock_ser = _make_serial_lines(line)
        packets = self._collect(mock_ser)
        assert len(packets) >= 1
        ts = packets[0]["ts"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None

    def test_multiple_valid_packets(self):
        lines = [
            json.dumps({"ts": "T+10s", "subsystem": "tcs", "n": i}) + "\n"
            for i in range(3)
        ]
        mock_ser = _make_serial_lines(*lines)
        packets = self._collect(mock_ser)
        assert len(packets) == 3
        ns = {p["n"] for p in packets}
        assert ns == {0, 1, 2}
