from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 2
_RETRY_DELAY_S  = 1.0


class BeamwardenClient:
    """
    Minimal client for Beamwarden's Beamrider telemetry ingest endpoint.

    Authenticates as a Beamrider device using a bearer token.
    Device identity is derived server-side from the token — not sent in the body.

    A single persistent httpx.Client is reused across all ingest calls to avoid
    the overhead of a new TCP connection per reading (satlab can produce up to
    ~18 calls per minute at maximum cadence on an RPi 3).
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(timeout=10.0)

    def ingest(self, sensor_name: str, recorded_at: datetime, payload: dict) -> bool:
        """
        POST a single reading to /api/v1/readings/ingest.

        Retries once on transient network errors. Returns True on success,
        False if all attempts fail (logs the reason on each failure).
        """
        body = {
            "sensor_name": sensor_name,
            "recorded_at": recorded_at.isoformat(),
            "payload": payload,
        }
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                resp = self._client.post(
                    f"{self._base_url}/api/v1/ingest/",
                    headers=self._headers,
                    json=body,
                )
                if resp.status_code == 201:
                    return True
                logger.warning(
                    "ingest rejected (attempt %d/%d): status=%d sensor=%s body=%s",
                    attempt, _RETRY_ATTEMPTS, resp.status_code, sensor_name, resp.text[:200],
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "ingest request failed (attempt %d/%d): %s",
                    attempt, _RETRY_ATTEMPTS, exc,
                )
                if attempt < _RETRY_ATTEMPTS:
                    time.sleep(_RETRY_DELAY_S)
        return False
