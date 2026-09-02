from __future__ import annotations

import logging
import time
from typing import Callable

from kidsspotifyplayer.adapters.spotify.device_discovery import (
    SpotifyConnectDeviceUnavailableError,
    SpotifyDeviceClient,
    resolve_device_id,
)
from kidsspotifyplayer.health import HealthRegistry


class StartupReadinessTimeoutError(RuntimeError):
    pass


def wait_for_spotify_connect_target(
    client: SpotifyDeviceClient,
    device_name: str,
    health_registry: HealthRegistry,
    *,
    discovery_interval_seconds: float = 1.0,
    timeout_seconds: float = 30.0,
    monotonic: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
    logger: logging.Logger | None = None,
) -> str:
    interval = _positive_real(
        discovery_interval_seconds,
        "discovery_interval_seconds",
    )
    timeout = _positive_real(timeout_seconds, "timeout_seconds")
    monotonic = monotonic or time.monotonic
    sleep = sleep or time.sleep
    logger = logger or logging.getLogger(__name__)
    deadline = monotonic() + timeout
    attempt = 0

    while True:
        attempt += 1
        try:
            device_id = resolve_device_id(
                client,
                device_name,
                health_registry=health_registry,
                report_unavailable=False,
            )
        except SpotifyConnectDeviceUnavailableError as error:
            now = monotonic()
            remaining = deadline - now
            if remaining <= 0:
                reason = (
                    f"Spotify Connect device '{device_name.strip()}' unavailable "
                    f"after {timeout:.1f} seconds"
                )
                health_registry.unhealthy(
                    "spotify_connect_target",
                    reason,
                    details={"attempts": attempt},
                )
                raise StartupReadinessTimeoutError(reason) from error

            if attempt == 1 or attempt % 5 == 0:
                logger.info(
                    "waiting for Spotify Connect device name=%r "
                    "attempt=%d remaining_seconds=%.1f",
                    device_name.strip(),
                    attempt,
                    remaining,
                )
            sleep(min(interval, remaining))
            continue

        logger.info(
            "Spotify Connect device ready name=%r device_id=%r attempts=%d",
            device_name.strip(),
            device_id,
            attempt,
        )
        return device_id


def _positive_real(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive number")
    if value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return float(value)
