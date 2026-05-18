from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

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
        with patch("orbit._fetch_tle_spacetrack", return_value=None):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate(datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc))
            assert isinstance(state, OrbitalState)

    def test_to_payload_after_fallback(self):
        with patch("orbit._fetch_tle_spacetrack", return_value=None):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate(datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc))
            payload = state.to_payload()
            assert "norad_id" in payload
            assert "error_code" in payload


# ── OrbitalPropagator — live TLE ─────────────────────────────────────────────

class TestOrbitalPropagatorLiveTle:
    def test_uses_fetched_tle(self):
        with patch("orbit._fetch_tle_spacetrack", return_value=_FALLBACK_TLE):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            now = datetime.now(timezone.utc)
            state = prop.propagate(now)
            assert isinstance(state, OrbitalState)

    def test_propagate_default_time_is_now(self):
        with patch("orbit._fetch_tle_spacetrack", return_value=_FALLBACK_TLE):
            prop = OrbitalPropagator(_DEFAULT_NORAD_ID)
            state = prop.propagate()
            assert state.timestamp_utc.tzinfo is not None


# ── _fetch_tle_spacetrack — missing credentials ───────────────────────────────

class TestFetchTleSpacetrack:
    def test_returns_none_without_credentials(self):
        from orbit import _fetch_tle_spacetrack
        with patch.dict(os.environ, {"SPACETRACK_USER": "", "SPACETRACK_PASS": ""}, clear=False):
            result = _fetch_tle_spacetrack("25544")
            assert result is None

    def test_returns_none_when_user_missing(self):
        from orbit import _fetch_tle_spacetrack
        env = {k: v for k, v in os.environ.items() if k not in ("SPACETRACK_USER", "SPACETRACK_PASS")}
        with patch.dict(os.environ, env, clear=True):
            result = _fetch_tle_spacetrack("25544")
            assert result is None
