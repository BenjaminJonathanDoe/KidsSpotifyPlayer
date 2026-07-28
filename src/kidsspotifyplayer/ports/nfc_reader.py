from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NfcReader(Protocol):
    """Port for reading NFC card identifiers."""

    def read_card_id(self) -> str | None:
        """Return the currently detected card identifier, if any."""
