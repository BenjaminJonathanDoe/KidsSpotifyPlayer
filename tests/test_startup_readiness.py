from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kidsspotifyplayer.health import HealthRegistry, HealthStatus
from kidsspotifyplayer.startup_readiness import (
    StartupReadinessTimeoutError,
    wait_for_spotify_connect_target,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class SequencedDeviceClient:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def devices(self) -> dict[str, Any]:
        self.calls += 1
        response = (
            self._responses.pop(0)
            if len(self._responses) > 1
            else self._responses[0]
        )
        if isinstance(response, Exception):
            raise response
        return response  # type: ignore[return-value]


def available_response() -> dict[str, Any]:
    return {
        "devices": [
            {
                "name": "KidsSpotifyPlayer",
                "id": "device-123",
            }
        ]
    }


def test_device_available_immediately_requires_no_retry_sleep() -> None:
    clock = FakeClock()
    client = SequencedDeviceClient([available_response()])
    registry = HealthRegistry(monotonic=clock.monotonic)

    device_id = wait_for_spotify_connect_target(
        client,
        "KidsSpotifyPlayer",
        registry,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert device_id == "device-123"
    assert client.calls == 1
    assert clock.sleeps == []


def test_device_can_appear_during_readiness_window() -> None:
    clock = FakeClock()
    client = SequencedDeviceClient(
        [
            {"devices": []},
            {"devices": []},
            available_response(),
        ]
    )
    registry = HealthRegistry(monotonic=clock.monotonic)

    device_id = wait_for_spotify_connect_target(
        client,
        "KidsSpotifyPlayer",
        registry,
        discovery_interval_seconds=1.0,
        timeout_seconds=30.0,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert device_id == "device-123"
    assert client.calls == 3
    assert clock.sleeps == [1.0, 1.0]
    assert not registry.fatal_event.is_set()


def test_device_absence_becomes_fatal_only_at_readiness_timeout() -> None:
    clock = FakeClock()
    client = SequencedDeviceClient([{"devices": []}])
    registry = HealthRegistry(monotonic=clock.monotonic)

    with pytest.raises(
        StartupReadinessTimeoutError,
        match="unavailable after 3.0 seconds",
    ):
        wait_for_spotify_connect_target(
            client,
            "KidsSpotifyPlayer",
            registry,
            discovery_interval_seconds=1.0,
            timeout_seconds=3.0,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )

    assert clock.now == 3.0
    assert client.calls == 4
    assert registry.fatal_event.is_set()
    health = registry.snapshot()["spotify_connect_target"]
    assert health.status is HealthStatus.UNHEALTHY


def test_network_failure_during_readiness_fails_immediately() -> None:
    clock = FakeClock()
    client = SequencedDeviceClient([ConnectionError("network unavailable")])
    registry = HealthRegistry(monotonic=clock.monotonic)

    with pytest.raises(ConnectionError, match="network unavailable"):
        wait_for_spotify_connect_target(
            client,
            "KidsSpotifyPlayer",
            registry,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )

    assert clock.sleeps == []
    assert registry.snapshot()["spotify_web_api"].status is HealthStatus.UNHEALTHY


def test_authentication_failure_during_readiness_is_distinct() -> None:
    class AuthenticationError(Exception):
        http_status = 401

    clock = FakeClock()
    client = SequencedDeviceClient([AuthenticationError("token expired")])
    registry = HealthRegistry(monotonic=clock.monotonic)

    with pytest.raises(AuthenticationError, match="token expired"):
        wait_for_spotify_connect_target(
            client,
            "KidsSpotifyPlayer",
            registry,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )

    snapshot = registry.snapshot()
    assert snapshot["spotify_authentication"].status is HealthStatus.UNHEALTHY
    assert snapshot["spotify_web_api"].status is HealthStatus.HEALTHY
    assert clock.sleeps == []
