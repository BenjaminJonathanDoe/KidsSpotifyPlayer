from __future__ import annotations

from typing import Protocol, runtime_checkable

from kidsspotifyplayer.domain.models import PlaybackTarget


@runtime_checkable
class ConfigRepository(Protocol):
    """Port for resolving card IDs to playback targets."""

    def find_playback_target(self, card_id: str) -> PlaybackTarget | None:
        """Resolve a card identifier to a playback target if configured."""
