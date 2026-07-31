from __future__ import annotations

import json
import sys
import threading
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


class RecordingSpotifyPlayer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []

    def play_context(self, target: PlaybackTarget) -> None:
        self.calls.append(("play_context", target))

    def toggle_play_pause(self) -> None:
        self.calls.append(("toggle_play_pause", None))

    def next_track(self) -> None:
        self.calls.append(("next_track", None))

    def previous_track(self) -> None:
        self.calls.append(("previous_track", None))

    def volume_up(self) -> None:
        self.calls.append(("volume_up", None))

    def volume_down(self) -> None:
        self.calls.append(("volume_down", None))


class RecordingFeedbackOutput:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def show_playing(self) -> None:
        self.calls.append("show_playing")

    def show_paused(self) -> None:
        self.calls.append("show_paused")

    def show_error(self, reason: str) -> None:
        self.calls.append(f"show_error:{reason}")


class BlockingSpotifyPlayer(RecordingSpotifyPlayer):
    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def play_context(self, target: PlaybackTarget) -> None:
        self.calls.append(("play_context", target))
        self.entered.set()
        self.release.wait(timeout=5)


def write_config(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_application(tmp_path: Path, config_payload: object) -> tuple[Application, RecordingSpotifyPlayer, RecordingFeedbackOutput]:
    config_path = tmp_path / "config.json"
    write_config(config_path, config_payload)
    spotify_player = RecordingSpotifyPlayer()
    feedback_output = RecordingFeedbackOutput()
    application = Application(
        config_path=config_path,
        spotify_player=spotify_player,
        feedback_output=feedback_output,
    )
    return application, spotify_player, feedback_output


def test_known_nfc_card_starts_configured_spotify_target(tmp_path: Path) -> None:
    application, spotify_player, feedback_output = build_application(
        tmp_path,
        {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}},
    )

    accepted = application.input_coordinator.publish(NfcCardDetected("04A1B2C3"))

    assert accepted is True
    assert spotify_player.calls == [("play_context", PlaybackTarget(uri="spotify:playlist:123456"))]
    assert feedback_output.calls == []


def test_card_id_normalization_works_across_the_application(tmp_path: Path) -> None:
    application, spotify_player, feedback_output = build_application(
        tmp_path,
        {"cards": {" 04a1b2c3 ": {"uri": "spotify:playlist:654321"}}},
    )

    accepted = application.input_coordinator.publish(NfcCardDetected("04A1B2C3"))

    assert accepted is True
    assert spotify_player.calls == [("play_context", PlaybackTarget(uri="spotify:playlist:654321"))]
    assert feedback_output.calls == []


def test_unknown_nfc_card_does_not_start_playback(tmp_path: Path) -> None:
    application, spotify_player, feedback_output = build_application(
        tmp_path,
        {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}},
    )

    accepted = application.input_coordinator.publish(NfcCardDetected("unknown"))

    assert accepted is True
    assert spotify_player.calls == []
    assert feedback_output.calls == ["show_error:Unknown card: unknown"]


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
def test_button_commands_are_routed_end_to_end(
    tmp_path: Path,
    event: object,
    expected_command: str,
) -> None:
    application, spotify_player, feedback_output = build_application(
        tmp_path,
        {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}},
    )

    accepted = application.input_coordinator.publish(event)

    assert accepted is True
    assert spotify_player.calls == [(expected_command, None)]
    assert feedback_output.calls == []


def test_input_serialization_is_preserved_across_the_complete_graph(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}})

    spotify_player = BlockingSpotifyPlayer()
    feedback_output = RecordingFeedbackOutput()
    application = Application(
        config_path=config_path,
        spotify_player=spotify_player,
        feedback_output=feedback_output,
    )

    first_result: bool | None = None
    second_result: bool | None = None

    def publish_first() -> None:
        nonlocal first_result
        first_result = application.input_coordinator.publish(NfcCardDetected("04A1B2C3"))

    first_thread = threading.Thread(target=publish_first)
    first_thread.start()

    assert spotify_player.entered.wait(timeout=2)

    def publish_second() -> None:
        nonlocal second_result
        second_result = application.input_coordinator.publish(PlayPausePressed())

    second_thread = threading.Thread(target=publish_second)
    second_thread.start()
    second_thread.join(timeout=2)

    assert second_result is False
    assert first_result is None

    spotify_player.release.set()
    first_thread.join(timeout=2)

    assert first_result is True

    later_result = application.input_coordinator.publish(PlayPausePressed())
    assert later_result is True
    assert spotify_player.calls[0][0] == "play_context"
    assert feedback_output.calls == []
