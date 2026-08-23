from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from crosslink import (
    MAX_PAYLOAD_BYTES,
    CrosslinkTransceiver,
    decode_compact,
    encode_compact,
)


def _vector_payload(**overrides) -> dict:
    base = {
        "node_id": "a1b2c3d4-0000-0000-0000-000000000000",
        "timestamp": "2026-08-23T12:00:00+00:00",
        "sequence": 42,
        "state": "NOMINAL",
        "mission_capability": 0.95,
        "available_for_tasking": True,
        "subsystems": {"adcs": {"state": "NOMINAL", "active_faults": [], "ae_score": 0.0}},
        "ae_summaries": {"adcs": 0.0},
        "nis_summaries": {},
        "hmac_tag": None,
    }
    base.update(overrides)
    return base


# ── encode_compact / decode_compact ────────────────────────────────────────

class TestEncodeCompact:
    def test_encodes_required_fields(self):
        encoded = encode_compact(_vector_payload())
        decoded = decode_compact(encoded)
        assert decoded["sequence"] == 42
        assert decoded["state"] == "NOMINAL"
        assert decoded["mission_capability"] == 0.95
        assert decoded["available_for_tasking"] is True

    @pytest.mark.parametrize("state", ["NOMINAL", "DEGRADED", "CRITICAL", "SAFE_MODE", "SILENT"])
    def test_round_trips_every_state(self, state):
        encoded = encode_compact(_vector_payload(state=state))
        decoded = decode_compact(encoded)
        assert decoded["state"] == state

    def test_unknown_state_raises(self):
        with pytest.raises(ValueError, match="unknown health state"):
            encode_compact(_vector_payload(state="BOGUS"))

    def test_available_for_tasking_false_round_trips(self):
        encoded = encode_compact(_vector_payload(available_for_tasking=False))
        decoded = decode_compact(encoded)
        assert decoded["available_for_tasking"] is False

    def test_encoded_size_well_under_payload_budget(self):
        encoded = encode_compact(_vector_payload(sequence=999999999))
        assert len(encoded.encode("utf-8")) < MAX_PAYLOAD_BYTES

    def test_does_not_include_subsystem_detail(self):
        # The full vector payload's subsystem/fault detail must not appear in
        # the over-the-air packet -- that's the whole point of compacting.
        encoded = encode_compact(_vector_payload())
        assert "adcs" not in encoded
        assert "active_faults" not in encoded


class TestDecodeCompact:
    def test_malformed_json_raises_valueerror(self):
        with pytest.raises(ValueError, match="not a valid compact health vector"):
            decode_compact("not json at all")

    def test_missing_key_raises_valueerror(self):
        with pytest.raises(ValueError, match="not a valid compact health vector"):
            decode_compact('{"s": 1, "t": "N"}')  # missing c, a

    def test_unknown_state_code_raises_valueerror(self):
        with pytest.raises(ValueError, match="not a valid compact health vector"):
            decode_compact('{"s": 1, "t": "Q", "c": 0.5, "a": 1}')

    def test_plain_text_message_raises_valueerror(self):
        # Other traffic on the shared channel (e.g. a human test message)
        # must be rejected, not crash the receive loop.
        with pytest.raises(ValueError):
            decode_compact("ping")


# ── CrosslinkTransceiver ────────────────────────────────────────────────────

@pytest.fixture
def mock_meshtastic():
    """Patch the lazily-imported meshtastic/pubsub modules crosslink.py pulls
    in inside CrosslinkTransceiver.__init__, and return the mock iface."""
    mock_iface_cls = MagicMock()
    mock_iface = MagicMock()
    mock_iface_cls.return_value = mock_iface
    mock_pub = MagicMock()
    with patch("meshtastic.serial_interface.SerialInterface", mock_iface_cls), \
         patch("pubsub.pub", mock_pub):
        yield mock_iface, mock_pub


class TestCrosslinkTransceiverInit:
    def test_opens_serial_interface_on_given_port(self, mock_meshtastic):
        mock_iface, _ = mock_meshtastic
        CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        # Constructed via the patched class -- port passed through.
        import meshtastic.serial_interface as si
        si.SerialInterface.assert_called_once_with("/dev/ttyACM1")

    def test_subscribes_to_receive_text(self, mock_meshtastic):
        _, mock_pub = mock_meshtastic
        CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        mock_pub.subscribe.assert_called_once()
        args, _ = mock_pub.subscribe.call_args
        assert args[1] == "meshtastic.receive.text"


class TestSendHealthVector:
    def test_sends_encoded_payload_to_peer(self, mock_meshtastic):
        mock_iface, _ = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        ok = tc.send_health_vector(_vector_payload())
        assert ok is True
        mock_iface.sendText.assert_called_once()
        args, kwargs = mock_iface.sendText.call_args
        assert kwargs["destinationId"] == "!fe54bdf2"
        assert decode_compact(args[0])["sequence"] == 42

    def test_returns_false_on_encode_failure_without_raising(self, mock_meshtastic):
        mock_iface, _ = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        ok = tc.send_health_vector(_vector_payload(state="BOGUS"))
        assert ok is False
        mock_iface.sendText.assert_not_called()

    def test_returns_false_on_transport_exception_without_raising(self, mock_meshtastic):
        mock_iface, _ = mock_meshtastic
        mock_iface.sendText.side_effect = RuntimeError("radio not responding")
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        ok = tc.send_health_vector(_vector_payload())
        assert ok is False


class TestOnReceive:
    def _receive_handler(self, tc, mock_pub):
        """Extract the callback CrosslinkTransceiver registered with pub.subscribe."""
        args, _ = mock_pub.subscribe.call_args
        return args[0]

    def test_ignores_packet_from_non_peer(self, mock_meshtastic):
        _, mock_pub = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        callback = MagicMock()
        tc.on_peer_vector(callback)
        handler = self._receive_handler(tc, mock_pub)
        packet = {"fromId": "!someoneelse", "decoded": {"text": encode_compact(_vector_payload())}}
        handler(packet, None)
        callback.assert_not_called()

    def test_ignores_non_text_packet(self, mock_meshtastic):
        _, mock_pub = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        callback = MagicMock()
        tc.on_peer_vector(callback)
        handler = self._receive_handler(tc, mock_pub)
        packet = {"fromId": "!fe54bdf2", "decoded": {}}
        handler(packet, None)
        callback.assert_not_called()

    def test_ignores_malformed_text_from_peer(self, mock_meshtastic):
        _, mock_pub = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        callback = MagicMock()
        tc.on_peer_vector(callback)
        handler = self._receive_handler(tc, mock_pub)
        packet = {"fromId": "!fe54bdf2", "decoded": {"text": "not a health vector"}}
        handler(packet, None)
        callback.assert_not_called()

    def test_calls_callback_with_decoded_vector_from_peer(self, mock_meshtastic):
        _, mock_pub = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        callback = MagicMock()
        tc.on_peer_vector(callback)
        handler = self._receive_handler(tc, mock_pub)
        packet = {"fromId": "!fe54bdf2", "decoded": {"text": encode_compact(_vector_payload(sequence=7))}}
        handler(packet, None)
        callback.assert_called_once()
        (received,), _ = callback.call_args
        assert received["sequence"] == 7

    def test_no_callback_registered_does_not_raise(self, mock_meshtastic):
        _, mock_pub = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        handler = self._receive_handler(tc, mock_pub)
        packet = {"fromId": "!fe54bdf2", "decoded": {"text": encode_compact(_vector_payload())}}
        handler(packet, None)  # must not raise even with no callback registered


class TestClose:
    def test_close_closes_interface(self, mock_meshtastic):
        mock_iface, _ = mock_meshtastic
        tc = CrosslinkTransceiver("/dev/ttyACM1", "!fe54bdf2")
        tc.close()
        mock_iface.close.assert_called_once()
