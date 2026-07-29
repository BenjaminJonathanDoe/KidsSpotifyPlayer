from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SpotifyPlayer(Protocol):
    """Port for controlling Spotify playback."""

    def play_context(self, uri: str) -> None:
        """Start playback for the given Spotify context URI."""

    def pause(self) -> None:
        """Pause playback."""

    def resume(self) -> None:
        """Resume playback."""

    def next_track(self) -> None:
        """Skip to the next track."""

    def previous_track(self) -> None:
        """Return to the previous track."""

    def set_volume(self, volume_percent: int) -> None:
        """Set the playback volume to the given percentage."""
