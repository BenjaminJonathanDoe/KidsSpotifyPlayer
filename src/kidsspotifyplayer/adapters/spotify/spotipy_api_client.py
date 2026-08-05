from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SpotipyClientProtocol(Protocol):
    def start_playback(
        self,
        *,
        device_id: str,
        context_uri: str | None = None,
    ) -> None:
        ...

    def pause_playback(self, *, device_id: str) -> None:
        ...

    def next_track(self, *, device_id: str) -> None:
        ...

    def previous_track(self, *, device_id: str) -> None:
        ...

    def current_playback(self) -> dict[str, Any] | None:
        ...

    def volume(
        self,
        volume_percent: int,
        *,
        device_id: str,
    ) -> None:
        ...


class SpotipyApiClient:
    def __init__(self, client: object) -> None:
        if client is None or not isinstance(client, SpotipyClientProtocol):
            raise TypeError("client must provide Spotipy-compatible methods")

        self._client = client

    def start_playback(
        self,
        *,
        device_id: str,
        context_uri: str,
    ) -> None:
        self._client.start_playback(
            device_id=device_id,
            context_uri=context_uri,
        )

    def pause_playback(self, *, device_id: str) -> None:
        self._client.pause_playback(device_id=device_id)

    def start_or_resume_playback(self, *, device_id: str) -> None:
        self._client.start_playback(device_id=device_id)

    def next_track(self, *, device_id: str) -> None:
        self._client.next_track(device_id=device_id)

    def previous_track(self, *, device_id: str) -> None:
        self._client.previous_track(device_id=device_id)

    def current_playback(
        self,
        *,
        device_id: str,
    ) -> dict[str, Any] | None:
        del device_id
        return self._client.current_playback()

    def volume(self, *, device_id: str) -> int | None:
        state = self._client.current_playback()
        if not isinstance(state, dict):
            return None

        device = state.get("device")
        if not isinstance(device, dict):
            return None

        if device.get("id") != device_id:
            return None

        volume_percent = device.get("volume_percent")
        if isinstance(volume_percent, bool):
            return None

        if not isinstance(volume_percent, int):
            return None

        return volume_percent

    def set_volume(
        self,
        *,
        device_id: str,
        volume_percent: int,
    ) -> None:
        self._client.volume(
            volume_percent,
            device_id=device_id,
        )