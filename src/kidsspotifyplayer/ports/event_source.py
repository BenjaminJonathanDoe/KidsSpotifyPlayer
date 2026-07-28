from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EventSource(Protocol):
    """Lifecycle-controlled port for push-based event sources."""

    def start(self) -> None:
        """Begin monitoring and publishing domain events."""

    def stop(self) -> None:
        """Stop monitoring and release any resources."""
