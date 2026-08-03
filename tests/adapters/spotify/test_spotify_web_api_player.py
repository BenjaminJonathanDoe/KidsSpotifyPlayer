from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from kidsspotifyplayer.adapters.spotify.spotify_web_api_player import SpotifyWebApiPlayer
from kidsspotifyplayer.domain.models import PlaybackTarget
from kidsspotifyplayer.ports import SpotifyPlayer


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleep_calls: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.now += seconds


class FakeSpotifyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._playback_states: list[dict[str, Any] | None] = []
        self._playback_index = 0
        self._volume: int | None = None
        self.raise_on: str | None = None

    def start_playback(self, *, device_id: str, context_uri: str) -> None:
        self.calls.append(("start_playback", {"device_id": device_id, "context_uri": context_uri}))
        self._raise_if_needed("start_playback")

    def pause_playback(self, *, device_id: str) -> None:
        self.calls.append(("pause_playback", {"device_id": device_id}))
        self._raise_if_needed("pause_playback")

    def start_or_resume_playback(self, *, device_id: str) -> None:
        self.calls.append(("start_or_resume_playback", {"device_id": device_id}))
        self._raise_if_needed("start_or_resume_playback")

    def next_track(self, *, device_id: str) -> None:
        self.calls.append(("next_track", {"device_id": device_id}))
        self._raise_if_needed("next_track")

    def previous_track(self, *, device_id: str) -> None:
        self.calls.append(("previous_track", {"device_id": device_id}))
        self._raise_if_needed("previous_track")

    def current_playback(self, *, device_id: str) -> dict[str, Any] | None:
        self.calls.append(("current_playback", {"device_id": device_id}))
        self._raise_if_needed("current_playback")
        if self._playback_index < len(self._playback_states):
            state = self._playback_states[self._playback_index]
            self._playback_index += 1
            return state
        if self._playback_states:
            return self._playback_states[-1]
        return None

    def volume(self, *, device_id: str) -> int | None:
        self.calls.append(("volume", {"device_id": device_id}))
        self._raise_if_needed("volume")
        return self._volume

    def set_volume(self, *, device_id: str, volume_percent: int) -> None:
        self.calls.append(("set_volume", {"device_id": device_id, "volume_percent": volume_percent}))
        self._raise_if_needed("set_volume")

    def set_playback_states(self, states: list[dict[str, Any] | None]) -> None:
        self._playback_states = list(states)
        self._playback_index = 0

    def set_volume_value(self, volume: int | None) -> None:
        self._volume = volume

    def _raise_if_needed(self, method_name: str) -> None:
        if self.raise_on == method_name:
            raise RuntimeError(f"boom:{method_name}")


def test_constructor_rejects_empty_device_id() -> None:
    with pytest.raises(ValueError, match="device_id"):
        SpotifyWebApiPlayer(FakeSpotifyClient(), "   ")


def test_play_context_confirms_when_requested_context_and_device_match() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "device-123"}, "context": {"uri": "spotify:playlist:abc"}},
    ])
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))

    assert client.calls[0] == ("start_playback", {"device_id": "device-123", "context_uri": "spotify:playlist:abc"})
    assert client.calls[1] == ("current_playback", {"device_id": "device-123"})


def test_play_context_does_not_confirm_for_different_context() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "device-123"}, "context": {"uri": "spotify:playlist:other"}},
    ])
    clock = FakeClock()
    adapter = SpotifyWebApiPlayer(
        client,
        "device-123",
        confirmation_timeout_seconds=1.0,
        poll_interval_seconds=0.25,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(TimeoutError, match="playback confirmation"):
        adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))

    assert clock.sleep_calls == [0.25, 0.25, 0.25, 0.25]


def test_play_context_does_not_confirm_for_other_device() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "other-device"}, "context": {"uri": "spotify:playlist:abc"}},
    ])
    clock = FakeClock()
    adapter = SpotifyWebApiPlayer(
        client,
        "device-123",
        confirmation_timeout_seconds=1.0,
        poll_interval_seconds=0.25,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(TimeoutError, match="playback confirmation"):
        adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))

    assert clock.sleep_calls == [0.25, 0.25, 0.25, 0.25]


def test_play_context_does_not_confirm_when_device_data_missing() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "context": {"uri": "spotify:playlist:abc"}},
    ])
    clock = FakeClock()
    adapter = SpotifyWebApiPlayer(
        client,
        "device-123",
        confirmation_timeout_seconds=1.0,
        poll_interval_seconds=0.25,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(TimeoutError, match="playback confirmation"):
        adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))

    assert clock.sleep_calls == [0.25, 0.25, 0.25, 0.25]


def test_play_context_does_not_confirm_when_context_data_missing() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "device-123"}},
    ])
    clock = FakeClock()
    adapter = SpotifyWebApiPlayer(
        client,
        "device-123",
        confirmation_timeout_seconds=1.0,
        poll_interval_seconds=0.25,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(TimeoutError, match="playback confirmation"):
        adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))

    assert clock.sleep_calls == [0.25, 0.25, 0.25, 0.25]


def test_play_context_polls_until_requested_state_is_observed() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "device-123"}, "context": {"uri": "spotify:playlist:other"}},
        {"is_playing": True, "device": {"id": "device-123"}, "context": {"uri": "spotify:playlist:abc"}},
    ])

    sleep_calls: list[float] = []

    adapter = SpotifyWebApiPlayer(
        client,
        "device-123",
        confirmation_timeout_seconds=1.0,
        poll_interval_seconds=0.25,
        monotonic=lambda: 0.0,
        sleep=lambda seconds: sleep_calls.append(seconds),
    )

    adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 0.25


def test_toggle_pauses_active_playback_on_the_configured_device() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "device-123"}},
    ])
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.toggle_play_pause()

    assert client.calls[-1] == ("pause_playback", {"device_id": "device-123"})


def test_toggle_resumes_existing_paused_playback() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": False, "device": {"id": "device-123"}},
    ])
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.toggle_play_pause()

    assert client.calls[-1] == ("start_or_resume_playback", {"device_id": "device-123"})


def test_toggle_raises_runtime_error_when_current_playback_is_none() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([None])
    adapter = SpotifyWebApiPlayer(client, "device-123")

    with pytest.raises(RuntimeError, match="unavailable"):
        adapter.toggle_play_pause()


def test_toggle_uses_resume_for_active_playback_on_another_device() -> None:
    client = FakeSpotifyClient()
    client.set_playback_states([
        {"is_playing": True, "device": {"id": "other-device"}},
    ])
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.toggle_play_pause()

    assert client.calls[-1] == ("start_or_resume_playback", {"device_id": "device-123"})


def test_next_track_targets_configured_device() -> None:
    client = FakeSpotifyClient()
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.next_track()

    assert client.calls == [("next_track", {"device_id": "device-123"})]


def test_previous_track_targets_configured_device() -> None:
    client = FakeSpotifyClient()
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.previous_track()

    assert client.calls == [("previous_track", {"device_id": "device-123"})]


def test_volume_up_reads_current_volume_applies_step_and_sends_result() -> None:
    client = FakeSpotifyClient()
    client.set_volume_value(20)
    adapter = SpotifyWebApiPlayer(client, "device-123", volume_step=5)

    adapter.volume_up()

    assert client.calls[-1] == ("set_volume", {"device_id": "device-123", "volume_percent": 25})


def test_volume_down_reads_current_volume_applies_step_and_sends_result() -> None:
    client = FakeSpotifyClient()
    client.set_volume_value(20)
    adapter = SpotifyWebApiPlayer(client, "device-123", volume_step=5)

    adapter.volume_down()

    assert client.calls[-1] == ("set_volume", {"device_id": "device-123", "volume_percent": 15})


def test_volume_up_clamps_to_maximum() -> None:
    client = FakeSpotifyClient()
    client.set_volume_value(100)
    adapter = SpotifyWebApiPlayer(client, "device-123", minimum_volume=0, maximum_volume=70)

    adapter.volume_up()

    assert client.calls[-1] == ("set_volume", {"device_id": "device-123", "volume_percent": 70})


def test_volume_down_clamps_to_minimum() -> None:
    client = FakeSpotifyClient()
    client.set_volume_value(0)
    adapter = SpotifyWebApiPlayer(client, "device-123", minimum_volume=0, maximum_volume=70)

    adapter.volume_down()

    assert client.calls[-1] == ("set_volume", {"device_id": "device-123", "volume_percent": 0})


def test_remote_volume_zero_is_treated_as_valid() -> None:
    client = FakeSpotifyClient()
    client.set_volume_value(0)
    adapter = SpotifyWebApiPlayer(client, "device-123")

    adapter.volume_up()

    assert client.calls[-1] == ("set_volume", {"device_id": "device-123", "volume_percent": 5})


def test_unavailable_remote_volume_raises_clear_error() -> None:
    client = FakeSpotifyClient()
    client.set_volume_value(None)
    adapter = SpotifyWebApiPlayer(client, "device-123")

    with pytest.raises(RuntimeError, match="volume"):
        adapter.volume_up()


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"confirmation_timeout_seconds": 0}, "confirmation_timeout_seconds"),
        ({"confirmation_timeout_seconds": True}, "confirmation_timeout_seconds"),
        ({"poll_interval_seconds": 0}, "poll_interval_seconds"),
        ({"poll_interval_seconds": False}, "poll_interval_seconds"),
        ({"volume_step": 0}, "volume_step"),
        ({"volume_step": True}, "volume_step"),
        ({"minimum_volume": True}, "minimum_volume"),
        ({"maximum_volume": True}, "maximum_volume"),
        ({"minimum_volume": 101}, "minimum_volume"),
        ({"maximum_volume": -1}, "maximum_volume"),
        ({"minimum_volume": 90, "maximum_volume": 80}, "minimum_volume and maximum_volume"),
    ],
)
def test_invalid_constructor_values_raise_value_error(kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        SpotifyWebApiPlayer(FakeSpotifyClient(), "device-123", **kwargs)


def test_external_client_exceptions_propagate() -> None:
    client = FakeSpotifyClient()
    client.raise_on = "start_playback"
    adapter = SpotifyWebApiPlayer(client, "device-123")

    with pytest.raises(RuntimeError, match="boom:start_playback"):
        adapter.play_context(PlaybackTarget(uri="spotify:playlist:abc"))


def test_adapter_structurally_satisfies_spotify_player_protocol() -> None:
    client = FakeSpotifyClient()
    adapter = SpotifyWebApiPlayer(client, "device-123")

    assert isinstance(adapter, SpotifyPlayer)
