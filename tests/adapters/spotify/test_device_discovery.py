from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from kidsspotifyplayer.adapters.spotify.device_discovery import (
    resolve_device_id,
)


class FakeSpotifyClient:
    def __init__(
        self,
        response: dict[str, Any],
    ) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def devices(self) -> dict[str, Any]:
        self.calls.append(
            {
                "method": "devices",
            }
        )
        return self.response


def test_resolve_device_id_returns_exact_name_match() -> None:
    client = FakeSpotifyClient(
        {
            "devices": [
                {
                    "name": "Other",
                    "id": "other-id",
                },
                {
                    "name": "KidsSpotifyPlayer",
                    "id": "player-id",
                },
            ]
        }
    )

    assert (
        resolve_device_id(
            client,
            "KidsSpotifyPlayer",
        )
        == "player-id"
    )

    assert client.calls == [
        {
            "method": "devices",
        }
    ]


def test_resolve_device_id_trims_configured_name() -> None:
    client = FakeSpotifyClient(
        {
            "devices": [
                {
                    "name": "KidsSpotifyPlayer",
                    "id": "player-id",
                },
            ]
        }
    )

    assert (
        resolve_device_id(
            client,
            "  KidsSpotifyPlayer  ",
        )
        == "player-id"
    )


def test_resolve_device_id_requires_exact_name_match() -> None:
    client = FakeSpotifyClient(
        {
            "devices": [
                {
                    "name": "kidsspotifyplayer",
                    "id": "wrong-id",
                },
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="No Spotify Connect device",
    ):
        resolve_device_id(
            client,
            "KidsSpotifyPlayer",
        )


def test_resolve_device_id_raises_when_no_device_matches() -> None:
    client = FakeSpotifyClient(
        {
            "devices": [
                {
                    "name": "Other",
                    "id": "other-id",
                },
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="No Spotify Connect device",
    ):
        resolve_device_id(
            client,
            "KidsSpotifyPlayer",
        )


@pytest.mark.parametrize(
    "device_id",
    [
        None,
        "",
        "   ",
        123,
        True,
    ],
)
def test_resolve_device_id_raises_when_matching_device_has_no_usable_id(
    device_id: object,
) -> None:
    client = FakeSpotifyClient(
        {
            "devices": [
                {
                    "name": "KidsSpotifyPlayer",
                    "id": device_id,
                },
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="usable ID",
    ):
        resolve_device_id(
            client,
            "KidsSpotifyPlayer",
        )


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        "invalid",
        {},
        {"devices": None},
        {"devices": "invalid"},
    ],
)
def test_resolve_device_id_rejects_malformed_device_listing(
    response: object,
) -> None:
    client = FakeSpotifyClient(
        response,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="device listing is malformed",
    ):
        resolve_device_id(
            client,
            "KidsSpotifyPlayer",
        )


def test_resolve_device_id_skips_malformed_device_entries() -> None:
    client = FakeSpotifyClient(
        {
            "devices": [
                None,
                "invalid",
                {
                    "name": "KidsSpotifyPlayer",
                    "id": "player-id",
                },
            ]
        }
    )

    assert (
        resolve_device_id(
            client,
            "KidsSpotifyPlayer",
        )
        == "player-id"
    )


@pytest.mark.parametrize(
    "device_name",
    [
        "",
        "   ",
        None,
        123,
        True,
    ],
)
def test_resolve_device_id_rejects_invalid_device_name(
    device_name: object,
) -> None:
    client = FakeSpotifyClient(
        {
            "devices": [],
        }
    )

    with pytest.raises(
        ValueError,
        match="device_name",
    ):
        resolve_device_id(
            client,
            device_name,  # type: ignore[arg-type]
        )
