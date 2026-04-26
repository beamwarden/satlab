from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class BeamwardenClient:
    """
    Minimal client for Beamwarden's Beamrider telemetry ingest endpoint.

    Authenticates as a Beamrider device using a bearer token.
    Device identity is derived server-side from the token — not sent in the body.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def ingest(self, sensor_name: str, recorded_at: datetime, payload: dict) -> bool:
        """
        POST a single reading to /api/v1/readings/ingest.

        Returns True on success, False on any error (logs the reason).
        """
        body = {
            "sensor_name": sensor_name,
            "recorded_at": recorded_at.isoformat(),
            "payload": payload,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self._base_url}/api/v1/ingest/",
                    headers=self._headers,
                    json=body,
                )
            if resp.status_code == 201:
                return True
            logger.warning("ingest rejected: status=%d sensor=%s body=%s",
                           resp.status_code, sensor_name, resp.text[:200])
            return False
        except httpx.RequestError as exc:
            logger.error("ingest request failed: %s", exc)
            return False
