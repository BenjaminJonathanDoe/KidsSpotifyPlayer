from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from kidsspotifyplayer.adapters.spotify.spotipy_api_client import (
    is_spotify_authentication_error,
)
from kidsspotifyplayer.health import HealthRegistry


class SpotifyConnectDeviceUnavailableError(ValueError):
    """The configured Connect target is absent from a valid device listing."""


@runtime_checkable
class SpotifyDeviceClient(Protocol):
    def devices(self) -> dict[str, Any]:
        ...


def resolve_device_id(
    client: SpotifyDeviceClient,
    device_name: str,
    *,
    health_registry: HealthRegistry | None = None,
    report_unavailable: bool = True,
) -> str:
    if not isinstance(device_name, str) or not device_name.strip():
        raise ValueError("device_name must be a non-empty string")

    normalized_device_name = device_name.strip()

    if health_registry is not None:
        health_registry.register("spotify_web_api")
        health_registry.register("spotify_authentication")
        health_registry.register("spotify_connect_target")

    try:
        response = client.devices()
    except Exception as error:
        if health_registry is not None:
            reason = f"device discovery: {type(error).__name__}: {error}"
            if is_spotify_authentication_error(error):
                health_registry.unhealthy("spotify_authentication", reason)
            else:
                health_registry.unhealthy("spotify_web_api", reason)
        raise
    else:
        if health_registry is not None:
            health_registry.heartbeat(
                "spotify_web_api",
                operation_succeeded=True,
            )

    if not isinstance(response, dict):
        if health_registry is not None:
            health_registry.unhealthy(
                "spotify_connect_target",
                "Spotify device listing is malformed",
            )
        raise ValueError("Spotify device listing is malformed")

    devices = response.get("devices")

    if not isinstance(devices, list):
        if health_registry is not None:
            health_registry.unhealthy(
                "spotify_connect_target",
                "Spotify device listing is malformed",
            )
        raise ValueError("Spotify device listing is malformed")

    for device in devices:
        if not isinstance(device, dict):
            continue

        if device.get("name") != normalized_device_name:
            continue

        device_id = device.get("id")

        if isinstance(device_id, str) and device_id.strip():
            if health_registry is not None:
                health_registry.heartbeat(
                    "spotify_connect_target",
                    operation_succeeded=True,
                )
            return device_id.strip()

        reason = f"Spotify device '{normalized_device_name}' has no usable ID"
        if health_registry is not None and report_unavailable:
            health_registry.unhealthy("spotify_connect_target", reason)
        raise SpotifyConnectDeviceUnavailableError(reason)

    reason = (
        f"No Spotify Connect device named "
        f"'{normalized_device_name}' was found"
    )
    if health_registry is not None and report_unavailable:
        health_registry.unhealthy("spotify_connect_target", reason)
    raise SpotifyConnectDeviceUnavailableError(reason)
