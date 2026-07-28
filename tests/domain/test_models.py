from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.domain.models import PlaybackTarget, PlayerState


def test_player_state_has_expected_values() -> None:
    assert PlayerState.IDLE.value == "idle"
    assert PlayerState.PLAYING.value == "playing"
    assert PlayerState.PAUSED.value == "paused"
    assert PlayerState.ERROR.value == "error"


def test_playback_target_is_immutable() -> None:
    target = PlaybackTarget(uri="spotify:track:123", name="Song")

    assert target.uri == "spotify:track:123"
    assert target.name == "Song"

    with pytest.raises(FrozenInstanceError):
        target.name = "Other"
