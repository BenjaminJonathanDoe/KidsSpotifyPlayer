from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.domain.events import Event, PlayPausePressed
from kidsspotifyplayer.event_bus import EventBus


@dataclass(frozen=True, slots=True)
class DemoEvent(Event):
    value: int


@dataclass(frozen=True, slots=True)
class OtherEvent(Event):
    pass


def test_subscribers_are_called_in_registration_order() -> None:
    bus = EventBus()
    calls: list[str] = []

    bus.subscribe(DemoEvent, lambda event: calls.append(f"first:{event.value}"))
    bus.subscribe(DemoEvent, lambda event: calls.append(f"second:{event.value}"))

    bus.publish(DemoEvent(3))

    assert calls == ["first:3", "second:3"]


def test_duplicate_subscriptions_are_ignored() -> None:
    bus = EventBus()
    calls: list[int] = []
    handler = lambda event: calls.append(event.value)

    bus.subscribe(DemoEvent, handler)
    bus.subscribe(DemoEvent, handler)
    bus.publish(DemoEvent(7))

    assert calls == [7]


def test_unsubscribe_removes_registered_handler() -> None:
    bus = EventBus()
    calls: list[int] = []

    def handler(event: DemoEvent) -> None:
        calls.append(event.value)

    bus.subscribe(DemoEvent, handler)
    bus.unsubscribe(DemoEvent, handler)
    bus.publish(DemoEvent(11))

    assert calls == []


def test_unsubscribe_unknown_handler_is_a_noop() -> None:
    bus = EventBus()
    calls: list[int] = []

    def handler(event: DemoEvent) -> None:
        calls.append(event.value)

    bus.unsubscribe(DemoEvent, handler)
    bus.publish(DemoEvent(13))

    assert calls == []


def test_publish_only_calls_exact_event_type_subscribers() -> None:
    bus = EventBus()
    calls: list[str] = []

    bus.subscribe(DemoEvent, lambda event: calls.append("demo"))
    bus.subscribe(OtherEvent, lambda event: calls.append("other"))

    bus.publish(DemoEvent(1))

    assert calls == ["demo"]


def test_subscribing_to_event_does_not_receive_derived_events() -> None:
    bus = EventBus()
    calls: list[str] = []

    def handler(event: Event) -> None:
        calls.append(type(event).__name__)

    bus.subscribe(Event, handler)
    bus.publish(PlayPausePressed())
    bus.publish(DemoEvent(5))

    assert calls == []


def test_handler_can_unsubscribe_itself_during_dispatch() -> None:
    bus = EventBus()
    calls: list[int] = []

    def handler(event: DemoEvent) -> None:
        calls.append(event.value)
        bus.unsubscribe(DemoEvent, handler)

    bus.subscribe(DemoEvent, handler)
    bus.publish(DemoEvent(1))
    bus.publish(DemoEvent(2))

    assert calls == [1]


def test_handler_added_during_dispatch_is_not_called_until_next_publish() -> None:
    bus = EventBus()
    calls: list[int] = []

    def first_handler(event: DemoEvent) -> None:
        if event.value == 1:
            bus.subscribe(DemoEvent, second_handler)

    def second_handler(event: DemoEvent) -> None:
        calls.append(event.value)

    bus.subscribe(DemoEvent, first_handler)
    bus.publish(DemoEvent(1))
    bus.publish(DemoEvent(2))

    assert calls == [2]


def test_handler_exceptions_propagate() -> None:
    bus = EventBus()

    def failing_handler(event: DemoEvent) -> None:
        raise RuntimeError(f"boom:{event.value}")

    bus.subscribe(DemoEvent, failing_handler)

    with pytest.raises(RuntimeError, match="boom:4"):
        bus.publish(DemoEvent(4))
