from __future__ import annotations

import time
from typing import Any, Callable, Protocol, runtime_checkable

from kidsspotifyplayer.domain.models import PlaybackTarget
from kidsspotifyplayer.ports import SpotifyPlayer


@runtime_checkable
class SpotifyApiClient(Protocol):
    """Minimal client boundary used by the Spotify Web API adapter."""

    def start_playback(self, *, device_id: str, context_uri: str) -> None:
        ...

    def pause_playback(self, *, device_id: str) -> None:
        ...

    def start_or_resume_playback(self, *, device_id: str) -> None:
        ...

    def next_track(self, *, device_id: str) -> None:
        ...

    def previous_track(self, *, device_id: str) -> None:
        ...

    def current_playback(self, *, device_id: str) -> dict[str, Any] | None:
        ...

    def volume(self, *, device_id: str) -> int | None:
        ...

    def set_volume(self, *, device_id: str, volume_percent: int) -> None:
        ...


class SpotifyWebApiPlayer(SpotifyPlayer):
    """Translate application-facing Spotify operations to a Web API client."""

    def __init__(
        self,
        client: SpotifyApiClient,
        device_id: str,
        *,
        confirmation_timeout_seconds: float = 10.0,
        poll_interval_seconds: float = 0.25,
        volume_step: int = 5,
        minimum_volume: int = 0,
        maximum_volume: int = 70,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._client = client
        self._device_id = self._validate_device_id(device_id)
        self._confirmation_timeout_seconds = self._validate_positive_real(
            confirmation_timeout_seconds,
            "confirmation_timeout_seconds",
        )
        self._poll_interval_seconds = self._validate_positive_real(
            poll_interval_seconds,
            "poll_interval_seconds",
        )
        self._volume_step = self._validate_volume_step(volume_step)
        self._minimum_volume = self._validate_volume_limit(minimum_volume, "minimum_volume")
        self._maximum_volume = self._validate_volume_limit(maximum_volume, "maximum_volume")
        if not 0 <= self._minimum_volume <= self._maximum_volume <= 100:
            raise ValueError("minimum_volume and maximum_volume must stay within 0..100")
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or time.sleep

    def play_context(self, target: PlaybackTarget) -> None:
        self._client.start_playback(device_id=self._device_id, context_uri=target.uri)
        self._await_playback_confirmation(target.uri)

    def toggle_play_pause(self) -> None:
        state = self._client.current_playback(device_id=self._device_id)
        if state is None:
            raise RuntimeError("Spotify playback state is unavailable")
        if not isinstance(state, dict):
            raise RuntimeError("Spotify playback state is malformed")

        is_playing = state.get("is_playing")
        if not isinstance(is_playing, bool):
            raise RuntimeError("Spotify playback state is malformed")

        device = state.get("device")
        if is_playing:
            if isinstance(device, dict):
                device_id = device.get("id")
                if isinstance(device_id, str) and device_id == self._device_id:
                    self._client.pause_playback(device_id=self._device_id)
                    return

            self._client.start_or_resume_playback(device_id=self._device_id)
            return

        self._client.start_or_resume_playback(device_id=self._device_id)

    def next_track(self) -> None:
        self._client.next_track(device_id=self._device_id)

    def previous_track(self) -> None:
        self._client.previous_track(device_id=self._device_id)

    def volume_up(self) -> None:
        self._set_volume(self._volume_step)

    def volume_down(self) -> None:
        self._set_volume(-self._volume_step)

    def _await_playback_confirmation(self, expected_context_uri: str) -> None:
        deadline = self._monotonic() + self._confirmation_timeout_seconds
        while True:
            state = self._client.current_playback(device_id=self._device_id)
            if self._is_confirmed_playback(state, expected_context_uri):
                return

            now = self._monotonic()
            if now >= deadline:
                raise TimeoutError("playback confirmation timed out")

            self._sleep(min(self._poll_interval_seconds, deadline - now))

    def _set_volume(self, delta: int) -> None:
        current_volume = self._client.volume(device_id=self._device_id)
        if not isinstance(current_volume, int) or isinstance(current_volume, bool):
            raise RuntimeError("Spotify playback volume is unavailable")

        new_volume = current_volume + delta
        new_volume = max(self._minimum_volume, min(self._maximum_volume, new_volume))
        self._client.set_volume(device_id=self._device_id, volume_percent=new_volume)

    def _is_confirmed_playback(self, state: dict[str, Any] | None, expected_context_uri: str) -> bool:
        if not isinstance(state, dict):
            return False

        is_playing = state.get("is_playing")
        if is_playing is not True:
            return False

        device = state.get("device")
        if not isinstance(device, dict):
            return False

        device_id = device.get("id")
        if not isinstance(device_id, str) or device_id != self._device_id:
            return False

        context = state.get("context")
        if not isinstance(context, dict):
            return False

        context_uri = context.get("uri")
        return isinstance(context_uri, str) and context_uri == expected_context_uri

    @staticmethod
    def _validate_device_id(device_id: str) -> str:
        if not isinstance(device_id, str):
            raise ValueError("device_id must be a non-empty string")

        normalized = device_id.strip()
        if not normalized:
            raise ValueError("device_id must be a non-empty string")
        return normalized

    @staticmethod
    def _validate_positive_real(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a positive number")
        if value <= 0:
            raise ValueError(f"{name} must be a positive number")
        return float(value)

    @staticmethod
    def _validate_volume_step(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("volume_step must be a positive integer")
        if value <= 0:
            raise ValueError("volume_step must be a positive integer")
        return value

    @staticmethod
    def _validate_volume_limit(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        return value
