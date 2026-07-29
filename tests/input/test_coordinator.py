from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.domain.events import Event, PlayPausePressed
from kidsspotifyplayer.event_bus import EventBus
from kidsspotifyplayer.input import InputCoordinator


class DemoEvent(Event):
    pass


def test_first_event_is_accepted() -> None:
    bus = EventBus()
    coordinator = InputCoordinator(bus)
    calls: list[str] = []

    bus.subscribe(PlayPausePressed, lambda event: calls.append("accepted"))

    assert coordinator.publish(PlayPausePressed()) is True
    assert calls == ["accepted"]


def test_second_event_during_processing_is_discarded() -> None:
    bus = EventBus()
    coordinator = InputCoordinator(bus)
    first_started = threading.Event()
    allow_finish = threading.Event()
    results: list[bool] = []
    calls: list[str] = []

    def first_handler(event: PlayPausePressed) -> None:
        calls.append("first")
        first_started.set()
        assert allow_finish.wait(timeout=1)

    def second_handler(event: PlayPausePressed) -> None:
        calls.append("second")

    bus.subscribe(PlayPausePressed, first_handler)
    bus.subscribe(PlayPausePressed, second_handler)

    def publish_first() -> None:
        results.append(coordinator.publish(PlayPausePressed()))

    thread = threading.Thread(target=publish_first)
    thread.start()
    assert first_started.wait(timeout=1)

    second_result = coordinator.publish(PlayPausePressed())
    allow_finish.set()
    thread.join(timeout=1)

    assert results[0] is True
    assert second_result is False
    assert calls == ["first", "second"]


def test_lock_is_released_after_successful_processing() -> None:
    bus = EventBus()
    coordinator = InputCoordinator(bus)
    calls: list[str] = []

    bus.subscribe(PlayPausePressed, lambda event: calls.append("accepted"))

    assert coordinator.publish(PlayPausePressed()) is True
    assert coordinator.publish(PlayPausePressed()) is True
    assert calls == ["accepted", "accepted"]


def test_lock_is_released_after_exceptions() -> None:
    bus = EventBus()
    coordinator = InputCoordinator(bus)
    calls: list[str] = []
    raised = False

    def failing_handler(event: PlayPausePressed) -> None:
        nonlocal raised
        calls.append("failing")
        if not raised:
            raised = True
            raise RuntimeError("boom")

    def later_handler(event: PlayPausePressed) -> None:
        calls.append("later")

    bus.subscribe(PlayPausePressed, failing_handler)
    bus.subscribe(PlayPausePressed, later_handler)

    with pytest.raises(RuntimeError, match="boom"):
        coordinator.publish(PlayPausePressed())

    assert coordinator.publish(PlayPausePressed()) is True
    assert calls == ["failing", "failing", "later"]


def test_user_input_handlers_are_serialized() -> None:
    bus = EventBus()
    coordinator = InputCoordinator(bus)
    started = threading.Event()
    release = threading.Event()
    active = 0
    max_active = 0
    results: list[bool] = []

    def handler(event: PlayPausePressed) -> None:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        started.set()
        assert release.wait(timeout=1)
        active -= 1

    bus.subscribe(PlayPausePressed, handler)

    def publish_first() -> None:
        results.append(coordinator.publish(PlayPausePressed()))

    thread = threading.Thread(target=publish_first)
    thread.start()
    assert started.wait(timeout=1)

    second_result = coordinator.publish(PlayPausePressed())
    release.set()
    thread.join(timeout=1)

    assert results[0] is True
    assert second_result is False
    assert max_active == 1
