from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kidsspotifyplayer.bootstrap import build_runtime
import kidsspotifyplayer.bootstrap as bootstrap
from kidsspotifyplayer.health import HealthRegistry, HealthStatus
from kidsspotifyplayer.startup_readiness import StartupReadinessTimeoutError


class FakeNfcReader:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.start_calls = 0

    def start(self) -> None:
        self.started = True
        self.start_calls += 1

    def stop(self) -> None:
        self.stopped = True


class FakeSpotifyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def devices(self) -> dict[str, Any]:
        self.calls.append(
            (
                "devices",
                None,
            )
        )

        return {
            "devices": [
                {
                    "name": "KidsSpotifyPlayer",
                    "id": "device-123",
                }
            ]
        }

    def start_playback(
        self,
        *,
        device_id: str,
        context_uri: str | None = None,
    ) -> None:
        return None

    def pause_playback(
        self,
        *,
        device_id: str,
    ) -> None:
        return None

    def next_track(
        self,
        *,
        device_id: str,
    ) -> None:
        return None

    def previous_track(
        self,
        *,
        device_id: str,
    ) -> None:
        return None

    def current_playback(
        self,
    ) -> dict[str, object] | None:
        return None

    def volume(
        self,
        volume_percent: int,
        *,
        device_id: str,
    ) -> None:
        return None


class FakeFeedbackOutput:
    def show_playing(self) -> None:
        return None

    def show_paused(self) -> None:
        return None

    def show_error(self, reason: str) -> None:
        del reason


def test_build_runtime_wires_core_components(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"cards": {}}',
        encoding="utf-8",
    )

    nfc_reader = FakeNfcReader()
    spotify_client = FakeSpotifyClient()
    feedback_output = FakeFeedbackOutput()

    runtime = build_runtime(
        config_path=config_path,
        nfc_reader=nfc_reader,
        spotify_client=spotify_client,
        feedback_output=feedback_output,
        spotify_device_name="KidsSpotifyPlayer",
    )

    assert runtime["event_bus"] is not None
    assert runtime["input_coordinator"] is not None
    assert runtime["config_repository"] is not None
    assert runtime["spotify_player"] is not None
    assert runtime["controller"] is not None

    assert runtime["nfc_reader"] is nfc_reader
    assert runtime["feedback_output"] is feedback_output

    assert nfc_reader.started is True
    assert nfc_reader.start_calls == 1
    assert runtime["readiness_event"].is_set()

    assert spotify_client.calls == [
        (
            "devices",
            None,
        )
    ]
    runtime["health_monitor"].stop()


def test_build_runtime_can_use_explicit_device_id_without_discovery(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"cards": {}}',
        encoding="utf-8",
    )

    nfc_reader = FakeNfcReader()
    spotify_client = FakeSpotifyClient()

    runtime = build_runtime(
        config_path=config_path,
        nfc_reader=nfc_reader,
        spotify_client=spotify_client,
        feedback_output=FakeFeedbackOutput(),
        device_id="explicit-device-id",
    )

    assert runtime["spotify_player"] is not None

    assert spotify_client.calls == []
    assert nfc_reader.start_calls == 1
    runtime["health_monitor"].stop()


def test_spotipy_and_oauth_requests_have_explicit_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, dict[str, object]] = {}

    class FakeSpotifyOAuth:
        def __init__(self, **kwargs: object) -> None:
            calls["oauth"] = kwargs

    class FakeSpotify:
        def __init__(self, **kwargs: object) -> None:
            calls["spotify"] = kwargs

    for name in (
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_REDIRECT_URI",
        "SPOTIFY_TOKEN_CACHE_PATH",
    ):
        monkeypatch.setenv(name, "configured")
    monkeypatch.setattr(bootstrap, "SpotifyOAuth", FakeSpotifyOAuth)
    monkeypatch.setattr(bootstrap.spotipy, "Spotify", FakeSpotify)

    bootstrap._build_spotify_client()

    assert calls["oauth"]["requests_timeout"] == 10
    assert calls["spotify"]["requests_timeout"] == 5


def test_nfc_starts_once_only_after_device_readiness_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class DelayedSpotifyClient(FakeSpotifyClient):
        def __init__(self) -> None:
            super().__init__()
            self.discovery_calls = 0

        def devices(self) -> dict[str, Any]:
            self.discovery_calls += 1
            events.append(f"discovery:{self.discovery_calls}")
            if self.discovery_calls == 1:
                return {"devices": []}
            return super().devices()

    class OrderedNfcReader(FakeNfcReader):
        def start(self) -> None:
            events.append("nfc:start")
            super().start()

    original_health_monitor = bootstrap.HealthMonitor

    class OrderedHealthMonitor(original_health_monitor):
        def start(self) -> None:
            events.append("health_monitor:start")
            super().start()

    monkeypatch.setattr(bootstrap, "HealthMonitor", OrderedHealthMonitor)

    now = 0.0

    def monotonic() -> float:
        return now

    def sleep(seconds: float) -> None:
        nonlocal now
        events.append("readiness:sleep")
        now += seconds + 9.0

    config_path = tmp_path / "config.json"
    config_path.write_text('{"cards": {}}', encoding="utf-8")
    reader = OrderedNfcReader()
    registry = HealthRegistry(monotonic=monotonic)

    runtime = build_runtime(
        config_path=config_path,
        nfc_reader=reader,
        spotify_client=DelayedSpotifyClient(),
        feedback_output=FakeFeedbackOutput(),
        spotify_device_name="KidsSpotifyPlayer",
        health_registry=registry,
        startup_monotonic=monotonic,
        startup_sleep=sleep,
        readiness_callback=lambda: events.append("application:ready"),
    )

    assert events == [
        "discovery:1",
        "readiness:sleep",
        "discovery:2",
        "health_monitor:start",
        "nfc:start",
        "application:ready",
    ]
    assert reader.start_calls == 1
    assert runtime["readiness_event"].is_set()
    assert runtime["health_registry"].snapshot()[
        "main_runtime"
    ].last_heartbeat == 10.0
    runtime["health_monitor"].stop()


def test_nfc_does_not_start_when_readiness_times_out(
    tmp_path: Path,
) -> None:
    class MissingDeviceClient(FakeSpotifyClient):
        def devices(self) -> dict[str, Any]:
            return {"devices": []}

    now = 0.0

    def monotonic() -> float:
        return now

    def sleep(seconds: float) -> None:
        nonlocal now
        now += seconds

    config_path = tmp_path / "config.json"
    config_path.write_text('{"cards": {}}', encoding="utf-8")
    reader = FakeNfcReader()
    registry = HealthRegistry(monotonic=monotonic)

    with pytest.raises(StartupReadinessTimeoutError):
        build_runtime(
            config_path=config_path,
            nfc_reader=reader,
            spotify_client=MissingDeviceClient(),
            feedback_output=FakeFeedbackOutput(),
            spotify_device_name="KidsSpotifyPlayer",
            health_registry=registry,
            startup_discovery_interval_seconds=1.0,
            startup_readiness_timeout_seconds=3.0,
            startup_monotonic=monotonic,
            startup_sleep=sleep,
        )

    assert reader.start_calls == 0
    assert registry.snapshot()[
        "spotify_connect_target"
    ].status is HealthStatus.UNHEALTHY
