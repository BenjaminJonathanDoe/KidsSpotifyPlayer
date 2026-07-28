from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlayerState(str, Enum):
    """The current playback state of the player."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass(frozen=True)
class PlaybackTarget:
    """A playback target resolved from an NFC card or other input."""

    uri: str
    name: str | None = None
