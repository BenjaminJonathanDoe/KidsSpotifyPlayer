from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from kidsspotifyplayer.adapters.config.json_config_repository import (
    JSONConfigRepository,
)
from kidsspotifyplayer.adapters.raspberry_pi.pn532_nfc_reader import (
    Pn532NfcReader,
)
from kidsspotifyplayer.adapters.raspberry_pi.pn532_spi_client import (
    create_default_pn532_spi_client,
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
from kidsspotifyplayer.event_bus import EventBus
from kidsspotifyplayer.input import InputCoordinator
from kidsspotifyplayer.health import HealthMonitor, HealthRegistry
from kidsspotifyplayer.ports import FeedbackOutput


def build_runtime(
    *,
    config_path: str | Path,
    nfc_reader: Any | None = None,
    spotify_client: Any | None = None,
    feedback_output: FeedbackOutput | None = None,
    spotify_device_name: str | None = None,
    device_id: str | None = None,
    health_registry: HealthRegistry | None = None,
) -> dict[str, Any]:
    resolved_path = Path(config_path)

    event_bus = EventBus()
    input_coordinator = InputCoordinator(event_bus)
    config_repository = JSONConfigRepository(resolved_path)
    health_registry = health_registry or HealthRegistry()
    health_registry.register("main_runtime", stale_after_seconds=3.0)

    if feedback_output is None:
        feedback_output = _NullFeedbackOutput()

    if spotify_client is None:
        spotify_client = _build_spotify_client()

    resolved_device_name = (
        spotify_device_name
        or os.environ.get(
            "SPOTIFY_DEVICE_NAME",
            "KidsSpotifyPlayer",
        )
    )

    resolved_device_id = device_id or resolve_device_id(
        spotify_client,
        resolved_device_name,
        health_registry=health_registry,
    )

    spotify_api_client = SpotipyApiClient(
        spotify_client,
        health_registry=health_registry,
    )

    spotify_player = SpotifyWebApiPlayer(
        spotify_api_client,
        resolved_device_id,
    )

    controller = PlayerController(
        event_bus,
        spotify_player,
        config_repository,
        feedback_output,
    )
    controller.register_handlers()

    reader = nfc_reader

    if reader is None:
        reader = Pn532NfcReader(
            _default_pn532_client(),
            input_coordinator,
            health_registry=health_registry,
        )

    reader.start()
    health_monitor = HealthMonitor(health_registry)
    health_monitor.start()

    return {
        "event_bus": event_bus,
        "input_coordinator": input_coordinator,
        "config_repository": config_repository,
        "spotify_player": spotify_player,
        "controller": controller,
        "nfc_reader": reader,
        "feedback_output": feedback_output,
        "health_registry": health_registry,
        "health_monitor": health_monitor,
    }


def run_runtime(
    *,
    config_path: str | Path,
) -> dict[str, Any]:
    runtime = build_runtime(
        config_path=config_path,
    )

    return supervise_runtime(runtime)


def supervise_runtime(runtime: dict[str, Any]) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    try:
        while not runtime["health_registry"].fatal_event.wait(timeout=1.0):
            runtime["health_registry"].heartbeat("main_runtime")
        runtime["health_monitor"].check_once()
        failures = runtime["health_registry"].critical_failures()
        failure_names = ", ".join(failure.name for failure in failures)
        logger.critical(
            "runtime terminating for supervisor recovery; failed_components=%s",
            failure_names,
        )
        raise RuntimeError(
            f"critical runtime health failure: {failure_names}"
        )
    except KeyboardInterrupt:
        pass
    finally:
        try:
            runtime["nfc_reader"].stop()
        finally:
            runtime["health_monitor"].stop(timeout_seconds=2.0)

    return runtime


def _build_spotify_client() -> spotipy.Spotify:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI")
    token_cache_path = os.environ.get("SPOTIFY_TOKEN_CACHE_PATH")

    required_values = {
        "SPOTIFY_CLIENT_ID": client_id,
        "SPOTIFY_CLIENT_SECRET": client_secret,
        "SPOTIFY_REDIRECT_URI": redirect_uri,
        "SPOTIFY_TOKEN_CACHE_PATH": token_cache_path,
    }

    missing = [
        key
        for key, value in required_values.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing Spotify environment variables: "
            + ", ".join(missing)
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=(
            "user-read-playback-state "
            "user-modify-playback-state"
        ),
        cache_path=token_cache_path,
        open_browser=False,
        requests_timeout=10,
    )

    return spotipy.Spotify(
        auth_manager=auth_manager,
        requests_timeout=5,
    )


def _default_pn532_client() -> Any:
    return create_default_pn532_spi_client()


class _NullFeedbackOutput:
    def show_playing(self) -> None:
        return None

    def show_paused(self) -> None:
        return None

    def show_error(self, reason: str) -> None:
        del reason
