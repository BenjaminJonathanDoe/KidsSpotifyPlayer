from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from kidsspotifyplayer.adapters.spotify.spotipy_api_client import (
    SpotipyApiClient,
)
from kidsspotifyplayer.adapters.spotify.spotify_web_api_player import (
    SpotifyApiClient,
)
from kidsspotifyplayer.health import HealthRegistry, HealthStatus


class RecordingSpotipyClient:
    def __init__(
        self,
        playback_state: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[
            tuple[str, tuple[Any, ...], dict[str, Any]]
        ] = []
        self.playback_state = playback_state
        self.raise_on: str | None = None

    def start_playback(
        self,
        *,
        device_id: str,
        context_uri: str | None = None,
    ) -> None:
        arguments: dict[str, Any] = {
            "device_id": device_id,
        }

        if context_uri is not None:
            arguments["context_uri"] = context_uri

        self.calls.append(
            (
                "start_playback",
                (),
                arguments,
            )
        )
        self._raise_if_needed("start_playback")

    def pause_playback(self, *, device_id: str) -> None:
        self.calls.append(
            (
                "pause_playback",
                (),
                {"device_id": device_id},
            )
        )
        self._raise_if_needed("pause_playback")

    def next_track(self, *, device_id: str) -> None:
        self.calls.append(
            (
                "next_track",
                (),
                {"device_id": device_id},
            )
        )
        self._raise_if_needed("next_track")

    def previous_track(self, *, device_id: str) -> None:
        self.calls.append(
            (
                "previous_track",
                (),
                {"device_id": device_id},
            )
        )
        self._raise_if_needed("previous_track")

    def current_playback(self) -> dict[str, Any] | None:
        self.calls.append(
            (
                "current_playback",
                (),
                {},
            )
        )
        self._raise_if_needed("current_playback")
        return self.playback_state

    def volume(
        self,
        volume_percent: int,
        *,
        device_id: str,
    ) -> None:
        self.calls.append(
            (
                "volume",
                (volume_percent,),
                {"device_id": device_id},
            )
        )
        self._raise_if_needed("volume")

    def _raise_if_needed(self, method_name: str) -> None:
        if self.raise_on == method_name:
            raise RuntimeError(f"boom:{method_name}")


def test_start_playback_forwards_device_and_context() -> None:
    client = RecordingSpotipyClient()
    adapter = SpotipyApiClient(client)

    adapter.start_playback(
        device_id="device-123",
        context_uri="spotify:playlist:abc",
    )

    assert client.calls == [
        (
            "start_playback",
            (),
            {
                "device_id": "device-123",
                "context_uri": "spotify:playlist:abc",
            },
        )
    ]


def test_pause_playback_forwards_device_id() -> None:
    client = RecordingSpotipyClient()
    adapter = SpotipyApiClient(client)

    adapter.pause_playback(device_id="device-123")

    assert client.calls == [
        (
            "pause_playback",
            (),
            {"device_id": "device-123"},
        )
    ]


def test_start_or_resume_playback_uses_start_playback_without_context() -> None:
    client = RecordingSpotipyClient()
    adapter = SpotipyApiClient(client)

    adapter.start_or_resume_playback(device_id="device-123")

    assert client.calls == [
        (
            "start_playback",
            (),
            {
                "device_id": "device-123",
            },
        )
    ]


def test_next_track_forwards_device_id() -> None:
    client = RecordingSpotipyClient()
    adapter = SpotipyApiClient(client)

    adapter.next_track(device_id="device-123")

    assert client.calls == [
        (
            "next_track",
            (),
            {"device_id": "device-123"},
        )
    ]


def test_previous_track_forwards_device_id() -> None:
    client = RecordingSpotipyClient()
    adapter = SpotipyApiClient(client)

    adapter.previous_track(device_id="device-123")

    assert client.calls == [
        (
            "previous_track",
            (),
            {"device_id": "device-123"},
        )
    ]


def test_current_playback_calls_spotipy_without_device_argument() -> None:
    client = RecordingSpotipyClient(
        {
            "is_playing": True,
        }
    )
    adapter = SpotipyApiClient(client)

    result = adapter.current_playback(device_id="device-123")

    assert result == {"is_playing": True}
    assert client.calls == [
        (
            "current_playback",
            (),
            {},
        )
    ]


def test_current_playback_returns_original_response_unchanged() -> None:
    state = {
        "is_playing": True,
        "context": {
            "uri": "spotify:playlist:abc",
        },
    }
    client = RecordingSpotipyClient(state)
    adapter = SpotipyApiClient(client)

    result = adapter.current_playback(device_id="device-123")

    assert result is state


def test_volume_returns_matching_device_integer_volume() -> None:
    client = RecordingSpotipyClient(
        {
            "device": {
                "id": "device-123",
                "volume_percent": 42,
            },
        }
    )
    adapter = SpotipyApiClient(client)

    assert adapter.volume(device_id="device-123") == 42


def test_volume_treats_zero_as_valid() -> None:
    client = RecordingSpotipyClient(
        {
            "device": {
                "id": "device-123",
                "volume_percent": 0,
            },
        }
    )
    adapter = SpotipyApiClient(client)

    assert adapter.volume(device_id="device-123") == 0


def test_volume_returns_none_when_playback_state_is_none() -> None:
    client = RecordingSpotipyClient(None)
    adapter = SpotipyApiClient(client)

    assert adapter.volume(device_id="device-123") is None


def test_volume_returns_none_when_device_data_is_missing() -> None:
    client = RecordingSpotipyClient(
        {
            "is_playing": True,
        }
    )
    adapter = SpotipyApiClient(client)

    assert adapter.volume(device_id="device-123") is None


def test_volume_returns_none_when_state_belongs_to_another_device() -> None:
    client = RecordingSpotipyClient(
        {
            "device": {
                "id": "other-device",
                "volume_percent": 20,
            },
        }
    )
    adapter = SpotipyApiClient(client)

    assert adapter.volume(device_id="device-123") is None


@pytest.mark.parametrize(
    "volume_percent",
    [
        None,
        True,
        False,
        12.5,
        "20",
        [],
        {},
    ],
)
def test_volume_returns_none_for_missing_or_malformed_volume_values(
    volume_percent: object,
) -> None:
    client = RecordingSpotipyClient(
        {
            "device": {
                "id": "device-123",
                "volume_percent": volume_percent,
            },
        }
    )
    adapter = SpotipyApiClient(client)

    assert adapter.volume(device_id="device-123") is None


def test_set_volume_forwards_to_spotipy_with_device_id() -> None:
    client = RecordingSpotipyClient()
    adapter = SpotipyApiClient(client)

    adapter.set_volume(
        device_id="device-123",
        volume_percent=30,
    )

    assert client.calls == [
        (
            "volume",
            (30,),
            {
                "device_id": "device-123",
            },
        )
    ]


def test_spotipy_exceptions_propagate() -> None:
    client = RecordingSpotipyClient()
    client.raise_on = "start_playback"
    adapter = SpotipyApiClient(client)

    with pytest.raises(
        RuntimeError,
        match="boom:start_playback",
    ):
        adapter.start_playback(
            device_id="device-123",
            context_uri="spotify:playlist:abc",
        )


def test_adapter_structurally_satisfies_spotify_api_client_protocol() -> None:
    adapter = SpotipyApiClient(
        RecordingSpotipyClient(),
    )

    assert isinstance(adapter, SpotifyApiClient)


@pytest.mark.parametrize(
    "client",
    [
        None,
        object(),
    ],
)
def test_constructor_rejects_none_or_non_spotipy_client(
    client: object | None,
) -> None:
    with pytest.raises(TypeError, match="client"):
        SpotipyApiClient(client)


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("connection lost"),
        TimeoutError("request timed out"),
    ],
)
def test_network_failures_update_spotify_health_and_propagate(
    error: Exception,
) -> None:
    class FailingClient(RecordingSpotipyClient):
        def start_playback(
            self,
            *,
            device_id: str,
            context_uri: str | None = None,
        ) -> None:
            del device_id, context_uri
            raise error

    registry = HealthRegistry()
    adapter = SpotipyApiClient(
        FailingClient(),
        health_registry=registry,
    )

    with pytest.raises(type(error), match=str(error)):
        adapter.start_playback(
            device_id="device-123",
            context_uri="spotify:playlist:abc",
        )

    health = registry.snapshot()["spotify_web_api"]
    assert health.status is HealthStatus.UNHEALTHY
    assert type(error).__name__ in (health.last_error or "")
    assert registry.fatal_event.is_set()
