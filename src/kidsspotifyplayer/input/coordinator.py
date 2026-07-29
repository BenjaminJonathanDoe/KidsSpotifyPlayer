from __future__ import annotations

import threading

from kidsspotifyplayer.domain.events import Event
from kidsspotifyplayer.event_bus import EventBus


class InputCoordinator:
    """Serializes user-generated events so only one command runs at a time."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._lock = threading.Lock()

    def publish(self, event: Event) -> bool:
        if not self._lock.acquire(blocking=False):
            return False

        try:
            self._event_bus.publish(event)
            return True
        finally:
            self._lock.release()
