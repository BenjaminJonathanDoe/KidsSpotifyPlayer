from __future__ import annotations

from typing import Callable

from kidsspotifyplayer.domain.events import Event

Handler = Callable[[Event], None]


class EventBus:
    """A synchronous event bus that dispatches to exact event types.

    Subscription is idempotent: registering the same handler for the same event
    type twice does not create duplicates.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[Handler]] = {}

    def subscribe(self, event_type: type[Event], handler: Handler) -> None:
        handlers = self._subscribers.setdefault(event_type, [])
        if handler not in handlers:
            handlers.append(handler)

    def unsubscribe(self, event_type: type[Event], handler: Handler) -> None:
        handlers = self._subscribers.get(event_type)
        if handlers is None:
            return
        if handler in handlers:
            handlers.remove(handler)
            if not handlers:
                del self._subscribers[event_type]

    def publish(self, event: Event) -> None:
        handlers = self._subscribers.get(type(event))
        if handlers is None:
            return
        for handler in list(handlers):
            handler(event)
