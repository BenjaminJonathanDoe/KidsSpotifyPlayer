from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SpotifyDeviceClient(Protocol):
    def current_user_devices(self) -> dict[str, Any]:
        ...


def resolve_device_id(
    client: SpotifyDeviceClient,
    device_name: str,
) -> str:
    if not isinstance(device_name, str) or not device_name.strip():
        raise ValueError("device_name must be a non-empty string")

    normalized_device_name = device_name.strip()

    response = client.current_user_devices()

    if not isinstance(response, dict):
        raise ValueError("Spotify device listing is malformed")

    devices = response.get("devices")

    if not isinstance(devices, list):
        raise ValueError("Spotify device listing is malformed")

    for device in devices:
        if not isinstance(device, dict):
            continue

        if device.get("name") != normalized_device_name:
            continue

        device_id = device.get("id")

        if isinstance(device_id, str) and device_id.strip():
            return device_id.strip()

        raise ValueError(
            f"Spotify device '{normalized_device_name}' has no usable ID"
        )

    raise ValueError(
        f"No Spotify Connect device named "
        f"'{normalized_device_name}' was found"
    )