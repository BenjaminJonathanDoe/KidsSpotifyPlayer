from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FeedbackOutput(Protocol):
    """Port for showing simple visual or audible feedback."""

    def show_playing(self) -> None:
        """Display or emit the playing feedback state."""

    def show_paused(self) -> None:
        """Display or emit the paused feedback state."""

    def show_error(self, reason: str) -> None:
        """Display or emit an error feedback state."""
