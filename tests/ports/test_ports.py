from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.ports import (
    AudioOutput,
    ButtonInput,
    ConfigRepository,
    FeedbackOutput,
    NfcReader,
    SpotifyPlayer,
)


class FakeSpotifyPlayer:
    def play_context(self, uri: str) -> None:
        self._last_uri = uri

    def pause(self) -> None:
        return None

    def resume(self) -> None:
        return None

    def next_track(self) -> None:
        return None

    def previous_track(self) -> None:
        return None

    def set_volume(self, volume_percent: int) -> None:
        self._last_volume = volume_percent

    def __init__(self) -> None:
        self._last_uri: str | None = None
        self._last_volume: int | None = None


class FakeFeedbackOutput:
    def show_playing(self) -> None:
        return None

    def show_paused(self) -> None:
        return None

    def show_error(self, reason: str) -> None:
        return None


class FakeConfigRepository:
    def load(self) -> dict[str, object]:
        return {}

    def save(self, config: dict[str, object]) -> None:
        return None


class FakeNfcReader:
    def read_card_id(self) -> str | None:
        return "card-1"


class FakeButtonInput:
    def wait_for_press(self) -> str:
        return "play"


class FakeAudioOutput:
    def set_volume(self, volume_percent: int) -> None:
        return None

    def set_muted(self, muted: bool) -> None:
        return None


def test_protocols_are_structurally_satisfied() -> None:
    assert isinstance(FakeSpotifyPlayer(), SpotifyPlayer)
    assert isinstance(FakeFeedbackOutput(), FeedbackOutput)
    assert isinstance(FakeConfigRepository(), ConfigRepository)
    assert isinstance(FakeNfcReader(), NfcReader)
    assert isinstance(FakeButtonInput(), ButtonInput)
    assert isinstance(FakeAudioOutput(), AudioOutput)
