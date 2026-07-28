from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ButtonInput(Protocol):
    """Port for reading button press events."""

    def wait_for_press(self) -> str:
        """Block until a button press is observed and return its identifier."""
