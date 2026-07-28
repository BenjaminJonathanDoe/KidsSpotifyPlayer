from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioOutput(Protocol):
    """Port for controlling audio playback volume and mute state."""

    def set_volume(self, volume_percent: int) -> None:
        """Set the output volume to the given percentage."""

    def set_muted(self, muted: bool) -> None:
        """Enable or disable audio mute."""
