from __future__ import annotations

import os
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from kidsspotifyplayer.adapters.config.json_config_repository import (
    JSONConfigRepository,
)
from kidsspotifyplayer.adapters.spotify.device_discovery import (
    resolve_device_id,
)
from kidsspotifyplayer.adapters.spotify.spotipy_api_client import (
    SpotipyApiClient,
)
from kidsspotifyplayer.adapters.spotify.spotify_web_api_player import (
    SpotifyWebApiPlayer,
)
from kidsspotifyplayer.application.controller import PlayerController
from kidsspotifyplayer.domain.events import NfcCardDetected
from kidsspotifyplayer.event_bus import EventBus
from kidsspotifyplayer.input import InputCoordinator


class ConsoleFeedback:
    def show_playing(self) -> None:
        print("PLAYING")

    def show_paused(self) -> None:
        print("PAUSED")

    def show_error(self, reason: str) -> None:
        print(f"ERROR: {reason}")


def require_environment(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    config_path = (
        project_root
        / "scripts"
        / "simulation_cards.json"
    )

    token_cache_path = (
        project_root
        / "scripts"
        / ".spotify-cache"
    )

    client_id = require_environment(
        "SPOTIFY_CLIENT_ID"
    )
    client_secret = require_environment(
        "SPOTIFY_CLIENT_SECRET"
    )
    redirect_uri = require_environment(
        "SPOTIFY_REDIRECT_URI"
    )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=(
            "user-read-playback-state "
            "user-modify-playback-state"
        ),
        cache_path=str(token_cache_path),
        open_browser=True,
    )

    spotify = spotipy.Spotify(
        auth_manager=auth_manager,
    )

    devices_response = spotify.devices()
    devices = devices_response.get("devices", [])

    if not devices:
        raise RuntimeError(
            "Spotify reports no available Connect devices. "
            "Open Spotify on the target device first."
        )

    print()
    print("Available Spotify devices:")

    for device in devices:
        print(
            f"  {device.get('name')} "
            f"[{device.get('id')}]"
        )

    print()

    device_name = input(
        "Spotify device name: "
    ).strip()

    device_id = resolve_device_id(
        spotify,
        device_name,
    )

    spotify_api_client = SpotipyApiClient(
        spotify,
    )

    spotify_player = SpotifyWebApiPlayer(
        spotify_api_client,
        device_id,
    )

    event_bus = EventBus()
    input_coordinator = InputCoordinator(
        event_bus,
    )

    config_repository = JSONConfigRepository(
        config_path,
    )

    controller = PlayerController(
        event_bus,
        spotify_player,
        config_repository,
        ConsoleFeedback(),
    )
    controller.register_handlers()

    print()
    print("KidsSpotifyPlayer Spotify simulation")
    print("Enter an NFC ID.")
    print("Enter q to quit.")
    print()

    while True:
        card_id = input("NFC ID: ").strip()

        if card_id.lower() == "q":
            break

        try:
            input_coordinator.publish(
                NfcCardDetected(
                    card_id=card_id,
                )
            )
        except Exception as error:
            print(
                f"Spotify command failed: "
                f"{type(error).__name__}: {error}"
            )


if __name__ == "__main__":
    main()
    