from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from orbit import OrbitalState, OrbitalPropagator, _FALLBACK_TLE, _DEFAULT_NORAD_ID


# ── OrbitalState.to_payload() ────────────────────────────────────────────────

class TestOrbitalStateToPayload:
    def _make_state(self, **kwargs) -> OrbitalState:
        defaults = dict(
            norad_id="25544",
            timestamp_utc=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
            x_km=6371.0,
            y_km=0.0,
            z_km=0.0,
            vx_km_s=0.0,
            vy_km_s=7.7,
            vz_km_s=0.0,
            error_code=0,
        )
        defaults.update(kwargs)
        return OrbitalState(**defaults)

    def test_keys_present(self):
        payload = self._make_state().to_payload()
        expected = {"norad_id", "x_km", "y_km", "z_km", "vx_km_s", "vy_km_s", "vz_km_s", "error_code"}
        assert set(payload.keys()) == expected

    def test_norad_id_preserved(self):
        payload = self._make_state(norad_id="99999").to_payload()
        assert payload["norad_id"] == "99999"

    def test_error_code_zero(self):
        payload = self._make_state(error_code=0).to_payload()
        assert payload["error_code"] == 0

    def test_position_rounded_to_3dp(self):
        payload = self._make_state(x_km=1234.56789).to_payload()
        assert payload["x_km"] == round(1234.56789, 3)

    def test_velocity_rounded_to_6dp(self):
        payload = self._make_state(vx_km_s=7.123456789).to_payload()
        assert payload["vx_km_s"] == round(7.123456789, 6)

    def test_error_code_nonzero(self):
        payload = self._make_state(error_code=3).to_payload()
        assert payload["error_code"] == 3

    def test_error_state_positions_are_zero(self):
        state = self._make_state(x_km=0.0, y_km=0.0, z_km=0.0, error_code=1)
        payload = state.to_payload()
        assert payload["x_km"] == 0.0
        assert payload["y_km"] == 0.0
        assert payload["z_km"] == 0.0


# ── OrbitalPropagator — fallback TLE ─────────────────────────────────────────

class TestOrbitalPropagatorFallback:
    def test_propagates_without_credentials(self):
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("orbit.os.environ.get", return_value=None),
        ):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate(datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc))
            # Fallback TLE is old — error_code may be non-zero at extended range,
            # but the call must not raise.
            assert isinstance(state, OrbitalState)
            assert state.norad_id == _DEFAULT_NORAD_ID

    def test_fetch_failure_falls_back(self):
        with patch("orbit._fetch_tle", return_value=None):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate(datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc))
            assert isinstance(state, OrbitalState)

    def test_to_payload_after_fallback(self):
        with patch("orbit._fetch_tle", return_value=None):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate(datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc))
            payload = state.to_payload()
            assert "norad_id" in payload
            assert "error_code" in payload


# ── OrbitalPropagator — live TLE ─────────────────────────────────────────────

class TestOrbitalPropagatorLiveTle:
    def test_uses_fetched_tle(self):
        with patch("orbit._fetch_tle", return_value=_FALLBACK_TLE):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            now = datetime.now(timezone.utc)
            state = prop.propagate(now)
            assert isinstance(state, OrbitalState)

    def test_propagate_default_time_is_now(self):
        with patch("orbit._fetch_tle", return_value=_FALLBACK_TLE):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate()
            assert state.timestamp_utc.tzinfo is not None


# ── _fetch_tle — ne-body cache endpoint ──────────────────────────────────────

class TestFetchTleNebody:
    """Tests for _fetch_tle(), which reads TLEs from the ne-body cache API."""

    def _nebody_ok_response(self) -> MagicMock:
        """Build a mock httpx.Response matching the ne-body /tle/{id}/latest schema."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "norad_id": 25544,
            "epoch_utc": "2026-07-04T12:00:00Z",
            "tle_line1": _FALLBACK_TLE[0],
            "tle_line2": _FALLBACK_TLE[1],
            "fetched_at": "2026-07-04T12:05:00Z",
            "source": "space_track",
        }
        return mock_resp

    def test_returns_tle_tuple_on_success(self):
        """ne-body returns 200 with valid JSON — function extracts (line1, line2)."""
        from orbit import _fetch_tle
        with (
            patch.dict(os.environ, {"NEBODY_URL": "http://keep-0001:8000"}, clear=False),
            patch("orbit.httpx.get", return_value=self._nebody_ok_response()) as mock_get,
        ):
            result = _fetch_tle("25544")
            assert result == (_FALLBACK_TLE[0], _FALLBACK_TLE[1])
            mock_get.assert_called_once()
            called_url = mock_get.call_args.args[0]
            assert called_url == "http://keep-0001:8000/tle/25544/latest"

    def test_returns_none_on_connect_error(self):
        """ne-body unreachable (connection refused) — returns None without raising."""
        from orbit import _fetch_tle
        with (
            patch.dict(os.environ, {"NEBODY_URL": "http://keep-0001:8000"}, clear=False),
            patch("orbit.httpx.get", side_effect=httpx.ConnectError("Connection refused")),
        ):
            result = _fetch_tle("25544")
            assert result is None

    def test_returns_none_on_404(self):
        """ne-body returns 404 (object not in its cache) — returns None."""
        from orbit import _fetch_tle
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with (
            patch.dict(os.environ, {"NEBODY_URL": "http://keep-0001:8000"}, clear=False),
            patch("orbit.httpx.get", return_value=mock_resp),
        ):
            result = _fetch_tle("25544")
            assert result is None

    def test_returns_none_when_nebody_url_not_set(self):
        """NEBODY_URL not configured — returns None without calling httpx.get at all."""
        from orbit import _fetch_tle
        env_without_nebody = {k: v for k, v in os.environ.items() if k != "NEBODY_URL"}
        with (
            patch.dict(os.environ, env_without_nebody, clear=True),
            patch("orbit.httpx.get") as mock_get,
        ):
            result = _fetch_tle("25544")
            assert result is None
            mock_get.assert_not_called()

    def test_propagator_falls_back_when_nebody_unreachable(self):
        """Propagator degrades to _FALLBACK_TLE when ne-body is down."""
        with (
            patch.dict(os.environ, {"NEBODY_URL": "http://keep-0001:8000"}, clear=False),
            patch("orbit.httpx.get", side_effect=httpx.ConnectError("Connection refused")),
        ):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate(datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc))
            assert isinstance(state, OrbitalState)
            assert state.norad_id == _DEFAULT_NORAD_ID
