from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sgp4.api import Satrec, jday

logger = logging.getLogger(__name__)

_SPACETRACK_BASE = "https://www.space-track.org"
_LOGIN_URL       = f"{_SPACETRACK_BASE}/ajaxauth/login"

# TLE refresh floor — Space-Track rate-limits to one poll per 30 minutes.
_TLE_REFRESH_INTERVAL_S = 1800

# Default tracked object: ISS (ZARYA)
_DEFAULT_NORAD_ID = "25544"

# Epoch: 2024-04-24. Used only when Space-Track is unreachable and no prior fetch
# has been cached. Propagation accuracy degrades significantly beyond a few weeks
# of epoch age. To improve resilience, persist the last successfully fetched TLE
# to disk and reload it on startup before falling back to this constant.
_FALLBACK_TLE = (
    "1 25544U 98067A   24115.54791667  .00016717  00000-0  10270-3 0  9997",
    "2 25544  51.6400 208.9163 0006317 323.8373  36.2351 15.50037786449239",
)


@dataclass
class OrbitalState:
    norad_id: str
    timestamp_utc: datetime
    x_km: float
    y_km: float
    z_km: float
    vx_km_s: float
    vy_km_s: float
    vz_km_s: float
    error_code: int  # 0 = nominal; sgp4 error codes otherwise

    def to_payload(self) -> dict:
        return {
            "norad_id": self.norad_id,
            "x_km": round(self.x_km, 3),
            "y_km": round(self.y_km, 3),
            "z_km": round(self.z_km, 3),
            "vx_km_s": round(self.vx_km_s, 6),
            "vy_km_s": round(self.vy_km_s, 6),
            "vz_km_s": round(self.vz_km_s, 6),
            "error_code": self.error_code,
        }


def _fetch_tle_spacetrack(norad_id: str) -> tuple[str, str] | None:
    """
    Fetch the current TLE for norad_id from Space-Track.org.

    Reads SPACETRACK_USER and SPACETRACK_PASS from the environment.
    Returns (line1, line2) on success, None on any failure.
    """
    user = os.environ.get("SPACETRACK_USER")
    password = os.environ.get("SPACETRACK_PASS")
    if not user or not password:
        logger.warning("SPACETRACK_USER / SPACETRACK_PASS not set — using fallback TLE")
        return None

    query_url = (
        f"{_SPACETRACK_BASE}/basicspacedata/query/class/gp"
        f"/NORAD_CAT_ID/{norad_id}/orderby/TLE_LINE1 ASC/limit/1/format/tle"
    )

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.post(
                _LOGIN_URL,
                data={"identity": user, "password": password},
            )
            resp.raise_for_status()

            resp = client.get(query_url)
            resp.raise_for_status()

        lines = [l.strip() for l in resp.text.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]

        logger.warning("unexpected TLE response for NORAD %s: %r", norad_id, resp.text[:120])
    except httpx.RequestError as exc:
        logger.error("Space-Track request failed: %s", exc)
    except httpx.HTTPStatusError as exc:
        logger.error("Space-Track HTTP error: %s", exc)

    return None


class OrbitalPropagator:
    """
    Wraps sgp4 to propagate a tracked object to the current time.

    Fetches TLEs from Space-Track.org and caches them for
    _TLE_REFRESH_INTERVAL_S (30 min) to respect rate limits.
    Falls back to a bundled TLE when the network is unavailable.
    """

    def __init__(self, norad_id: str = _DEFAULT_NORAD_ID) -> None:
        self._norad_id    = norad_id
        self._last_fetch  = 0.0
        self._sat         = self._load()

    def _load(self) -> Satrec:
        tle = _fetch_tle_spacetrack(self._norad_id)
        if tle is None:
            logger.warning("using fallback TLE for NORAD %s", self._norad_id)
            tle = _FALLBACK_TLE
        sat = Satrec.twoline2rv(tle[0], tle[1])
        self._last_fetch = time.monotonic()
        logger.info("loaded TLE for NORAD %s (epoch year: %s)", self._norad_id, sat.epochyr)
        return sat

    def _maybe_refresh(self) -> None:
        if time.monotonic() - self._last_fetch >= _TLE_REFRESH_INTERVAL_S:
            logger.info("refreshing TLE for NORAD %s", self._norad_id)
            self._sat = self._load()

    def propagate(self, t: datetime | None = None) -> OrbitalState:
        """Propagate to t (default: now UTC) and return ECI state."""
        if t is None:
            t = datetime.now(timezone.utc)
        self._maybe_refresh()
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute,
                      t.second + t.microsecond / 1e6)
        e, r, v = self._sat.sgp4(jd, fr)
        return OrbitalState(
            norad_id=self._norad_id,
            timestamp_utc=t,
            x_km=r[0] if e == 0 else 0.0,
            y_km=r[1] if e == 0 else 0.0,
            z_km=r[2] if e == 0 else 0.0,
            vx_km_s=v[0] if e == 0 else 0.0,
            vy_km_s=v[1] if e == 0 else 0.0,
            vz_km_s=v[2] if e == 0 else 0.0,
            error_code=e,
        )
