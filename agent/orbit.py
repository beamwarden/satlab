from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sgp4.api import Satrec, jday

logger = logging.getLogger(__name__)

# TLE refresh interval. ne-body polls Space-Track at most once per 3600 s, so
# requesting the ne-body cache more often than that returns the same cached
# data. Align satlab's cadence to ne-body's ingest cycle.
_TLE_REFRESH_INTERVAL_S = 3600

# Default tracked object: ISS (ZARYA)
_DEFAULT_NORAD_ID = "25544"

# Epoch: 2024-04-24. Used only when ne-body is unreachable and no prior fetch
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


def _fetch_tle(norad_id: str) -> tuple[str, str] | None:
    """
    Fetch the current TLE for norad_id from the ne-body cache endpoint.

    Reads NEBODY_URL from the environment (e.g. http://keep-0001:8000).
    If unset, logs a warning and returns None immediately without making
    any HTTP call — the caller (_load) will use _FALLBACK_TLE.

    If NEBODY_API_KEY is set in the environment, it is forwarded to
    ne-body as a ?key=... query parameter. This satisfies ne-body's
    _ApiKeyMiddleware when auth is enabled on the ne-body server. The
    parameter is harmless when ne-body has no API key configured.

    Returns (line1, line2) on success, None on any failure (NEBODY_URL
    not set, connection error, timeout, non-200 status, malformed JSON,
    or missing fields). Never raises — the caller treats None as
    "use _FALLBACK_TLE".
    """
    nebody_url = os.environ.get("NEBODY_URL")
    if not nebody_url:
        logger.warning("NEBODY_URL not set — skipping TLE fetch, using fallback TLE")
        return None

    nebody_api_key = os.environ.get("NEBODY_API_KEY")
    url = f"{nebody_url}/tle/{norad_id}/latest"
    params: dict[str, str] = {"key": nebody_api_key} if nebody_api_key else {}

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        if response.status_code != 200:
            logger.warning(
                "ne-body returned HTTP %s for NORAD %s — using fallback TLE",
                response.status_code,
                norad_id,
            )
            return None

        data = response.json()
        line1: str = data["tle_line1"]
        line2: str = data["tle_line2"]
        return line1, line2

    except httpx.RequestError as exc:
        logger.warning(
            "ne-body unreachable for NORAD %s: %s — using fallback TLE",
            norad_id,
            exc,
        )
    except (KeyError, ValueError) as exc:
        logger.warning(
            "malformed ne-body response for NORAD %s: %s — using fallback TLE",
            norad_id,
            exc,
        )

    return None


class OrbitalPropagator:
    """
    Wraps sgp4 to propagate a tracked object to the current time.

    Fetches TLEs from the ne-body cache endpoint (NEBODY_URL env var) and
    caches them for _TLE_REFRESH_INTERVAL_S (3600 s) to match ne-body's
    own Space-Track polling cadence. Falls back to a bundled TLE when
    ne-body is unreachable or NEBODY_URL is not configured.
    """

    def __init__(self, norad_id: str = _DEFAULT_NORAD_ID) -> None:
        self._norad_id    = norad_id
        self._last_fetch  = 0.0
        self._sat         = self._load()

    def _load(self) -> Satrec:
        tle = _fetch_tle(self._norad_id)
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
