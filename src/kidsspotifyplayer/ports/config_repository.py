from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConfigRepository(Protocol):
    """Port for loading and storing configuration values."""

    def load(self) -> dict[str, object]:
        """Load the current configuration as a dictionary."""

    def save(self, config: dict[str, object]) -> None:
        """Persist a configuration dictionary."""
