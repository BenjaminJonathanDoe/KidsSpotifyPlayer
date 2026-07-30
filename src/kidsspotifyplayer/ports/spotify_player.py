from __future__ import annotations

from typing import Protocol, runtime_checkable

from kidsspotifyplayer.domain.models import PlaybackTarget


@runtime_checkable
class SpotifyPlayer(Protocol):
    """Port for controlling Spotify playback."""

    def play_context(self, target: PlaybackTarget) -> None:
        """Start playback for the given playback target."""

    def toggle_play_pause(self) -> None:
        """Toggle playback between playing and paused states."""

    def next_track(self) -> None:
        """Skip to the next track."""

    def previous_track(self) -> None:
        """Return to the previous track."""

    def volume_up(self) -> None:
        """Increase playback volume by the adapter's preferred step."""

    def volume_down(self) -> None:
        """Decrease playback volume by the adapter's preferred step."""
