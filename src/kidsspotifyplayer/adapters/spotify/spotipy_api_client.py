from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar, runtime_checkable

from kidsspotifyplayer.health import HealthRegistry

T = TypeVar("T")


def is_spotify_authentication_error(error: Exception) -> bool:
    status = getattr(error, "http_status", None)
    text = f"{type(error).__name__} {error}".lower()
    return status in (401, 403) or "auth" in text or "token" in text


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
    def __init__(
        self,
        client: object,
        *,
        health_registry: HealthRegistry | None = None,
    ) -> None:
        if client is None or not isinstance(client, SpotipyClientProtocol):
            raise TypeError("client must provide Spotipy-compatible methods")

        self._client = client
        self._health_registry = health_registry
        if health_registry is not None:
            health_registry.register("spotify_web_api")
            health_registry.register("spotify_authentication")

    def start_playback(
        self,
        *,
        device_id: str,
        context_uri: str,
    ) -> None:
        self._call(
            "start_playback",
            lambda: self._client.start_playback(
                device_id=device_id,
                context_uri=context_uri,
            ),
        )

    def pause_playback(self, *, device_id: str) -> None:
        self._call(
            "pause_playback",
            lambda: self._client.pause_playback(device_id=device_id),
        )

    def start_or_resume_playback(self, *, device_id: str) -> None:
        self._call(
            "start_or_resume_playback",
            lambda: self._client.start_playback(device_id=device_id),
        )

    def next_track(self, *, device_id: str) -> None:
        self._call("next_track", lambda: self._client.next_track(device_id=device_id))

    def previous_track(self, *, device_id: str) -> None:
        self._call(
            "previous_track",
            lambda: self._client.previous_track(device_id=device_id),
        )

    def current_playback(
        self,
        *,
        device_id: str,
    ) -> dict[str, Any] | None:
        del device_id
        return self._call("current_playback", self._client.current_playback)

    def volume(self, *, device_id: str) -> int | None:
        state = self._call("current_playback", self._client.current_playback)
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
        self._call(
            "set_volume",
            lambda: self._client.volume(
                volume_percent,
                device_id=device_id,
            ),
        )

    def _call(self, operation: str, call: Callable[[], T]) -> T:
        try:
            result = call()
        except Exception as error:
            if self._health_registry is not None:
                reason = f"{operation}: {type(error).__name__}: {error}"
                if is_spotify_authentication_error(error):
                    self._health_registry.unhealthy(
                        "spotify_authentication",
                        reason,
                    )
                else:
                    self._health_registry.unhealthy("spotify_web_api", reason)
            raise

        if self._health_registry is not None:
            self._health_registry.heartbeat(
                "spotify_web_api",
                operation_succeeded=True,
            )
        return result
