from __future__ import annotations

from typing import Protocol, runtime_checkable

from .event_source import EventSource


@runtime_checkable
class NfcReader(EventSource, Protocol):
    """Lifecycle-controlled port for NFC input event sources."""
