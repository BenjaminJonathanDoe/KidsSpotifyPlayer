from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.adapters.config.json_config_repository import JSONConfigRepository
from kidsspotifyplayer.domain.models import PlaybackTarget
from kidsspotifyplayer.ports import (
    AudioOutput,
    ButtonInput,
    ConfigRepository,
    EventSource,
    FeedbackOutput,
    NfcReader,
    SpotifyPlayer,
)


class FakeSpotifyPlayer:
    def play_context(self, target: PlaybackTarget) -> None:
        self._last_target = target

    def toggle_play_pause(self) -> None:
        return None

    def next_track(self) -> None:
        return None

    def previous_track(self) -> None:
        return None

    def volume_up(self) -> None:
        return None

    def volume_down(self) -> None:
        return None

    def __init__(self) -> None:
        self._last_target: PlaybackTarget | None = None


class FakeFeedbackOutput:
    def show_playing(self) -> None:
        return None

    def show_paused(self) -> None:
        return None

    def show_error(self, reason: str) -> None:
        return None


class FakeConfigRepository:
    def find_playback_target(self, card_id: str) -> PlaybackTarget | None:
        return None


class FakeNfcReader:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class FakeButtonInput:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class FakeAudioOutput:
    def set_volume(self, volume_percent: int) -> None:
        return None

    def set_muted(self, muted: bool) -> None:
        return None


def test_protocols_are_structurally_satisfied(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}}', encoding="utf-8")

    assert isinstance(FakeSpotifyPlayer(), SpotifyPlayer)
    assert isinstance(FakeFeedbackOutput(), FeedbackOutput)
    assert isinstance(FakeConfigRepository(), ConfigRepository)
    assert isinstance(JSONConfigRepository(config_path), ConfigRepository)
    assert isinstance(FakeNfcReader(), NfcReader)
    assert isinstance(FakeButtonInput(), ButtonInput)
    assert isinstance(FakeAudioOutput(), AudioOutput)
    assert isinstance(FakeButtonInput(), EventSource)
    assert isinstance(FakeNfcReader(), EventSource)


def test_old_polling_only_implementations_no_longer_satisfy_protocols() -> None:
    class PollingButtonInput:
        def wait_for_press(self) -> str:
            return "play"

    class PollingNfcReader:
        def read_card_id(self) -> str | None:
            return "card-1"

    assert not isinstance(PollingButtonInput(), ButtonInput)
    assert not isinstance(PollingNfcReader(), NfcReader)
