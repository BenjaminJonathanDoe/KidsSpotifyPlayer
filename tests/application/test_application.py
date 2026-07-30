from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.application import Application
from kidsspotifyplayer.domain.events import (
    NfcCardDetected,
    NextTrackPressed,
    PlayPausePressed,
    PreviousTrackPressed,
    VolumeDownPressed,
    VolumeUpPressed,
)
from kidsspotifyplayer.domain.models import PlaybackTarget


class FakeSpotifyPlayer:
    def __init__(self) -> None:
        self.last_target: PlaybackTarget | None = None
        self.last_command: str | None = None

    def play_context(self, target: PlaybackTarget) -> None:
        self.last_target = target
        self.last_command = "play_context"

    def toggle_play_pause(self) -> None:
        self.last_command = "toggle_play_pause"

    def next_track(self) -> None:
        self.last_command = "next_track"

    def previous_track(self) -> None:
        self.last_command = "previous_track"

    def volume_up(self) -> None:
        self.last_command = "volume_up"

    def volume_down(self) -> None:
        self.last_command = "volume_down"


class FakeFeedbackOutput:
    def __init__(self) -> None:
        self.last_error: str | None = None
        self.last_message: str | None = None

    def show_playing(self) -> None:
        self.last_message = "playing"

    def show_paused(self) -> None:
        self.last_message = "paused"

    def show_error(self, reason: str) -> None:
        self.last_error = reason
        self.last_message = reason


def write_config(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_application_constructs_and_registers_handlers(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}})

    spotify_player = FakeSpotifyPlayer()
    feedback_output = FakeFeedbackOutput()
    application = Application(
        config_path=config_path,
        spotify_player=spotify_player,
        feedback_output=feedback_output,
    )

    assert application.event_bus is not None
    assert application.input_coordinator is not None
    assert application.controller is not None
    assert application.spotify_player is spotify_player
    assert application.feedback_output is feedback_output


def test_nfc_event_routes_to_spotify_player(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}})

    spotify_player = FakeSpotifyPlayer()
    feedback_output = FakeFeedbackOutput()
    application = Application(
        config_path=config_path,
        spotify_player=spotify_player,
        feedback_output=feedback_output,
    )

    application.input_coordinator.publish(NfcCardDetected("04A1B2C3"))

    assert application.spotify_player.last_command == "play_context"
    assert application.spotify_player.last_target == PlaybackTarget(uri="spotify:playlist:123456")
    assert application.feedback_output.last_error is None


def test_unknown_card_triggers_feedback(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}})

    spotify_player = FakeSpotifyPlayer()
    feedback_output = FakeFeedbackOutput()
    application = Application(
        config_path=config_path,
        spotify_player=spotify_player,
        feedback_output=feedback_output,
    )

    application.input_coordinator.publish(NfcCardDetected("unknown"))

    assert application.spotify_player.last_command is None
    assert application.feedback_output.last_error == "Unknown card: unknown"


@pytest.mark.parametrize(
    ("event", "expected_command"),
    [
        (PlayPausePressed(), "toggle_play_pause"),
        (NextTrackPressed(), "next_track"),
        (PreviousTrackPressed(), "previous_track"),
        (VolumeUpPressed(), "volume_up"),
        (VolumeDownPressed(), "volume_down"),
    ],
)
def test_button_events_reach_spotify_player(tmp_path: Path, event: object, expected_command: str) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}})

    spotify_player = FakeSpotifyPlayer()
    feedback_output = FakeFeedbackOutput()
    application = Application(
        config_path=config_path,
        spotify_player=spotify_player,
        feedback_output=feedback_output,
    )

    application.input_coordinator.publish(event)

    assert application.spotify_player.last_command == expected_command
