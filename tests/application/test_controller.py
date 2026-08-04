from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.application import PlayerController
from kidsspotifyplayer.domain.events import (
    NfcCardDetected,
    NextTrackPressed,
    PlayPausePressed,
    PreviousTrackPressed,
    VolumeDownPressed,
    VolumeUpPressed,
)
from kidsspotifyplayer.domain.models import PlaybackTarget
from kidsspotifyplayer.event_bus import EventBus


class FakeSpotifyPlayer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []
        self.raise_on: str | None = None

    def play_context(self, target: PlaybackTarget) -> None:
        self._raise_if_needed("play_context")
        self.calls.append(("play_context", target))

    def toggle_play_pause(self) -> None:
        self._raise_if_needed("toggle_play_pause")
        self.calls.append(("toggle_play_pause", None))

    def next_track(self) -> None:
        self._raise_if_needed("next_track")
        self.calls.append(("next_track", None))

    def previous_track(self) -> None:
        self._raise_if_needed("previous_track")
        self.calls.append(("previous_track", None))

    def volume_up(self) -> None:
        self._raise_if_needed("volume_up")
        self.calls.append(("volume_up", None))

    def volume_down(self) -> None:
        self._raise_if_needed("volume_down")
        self.calls.append(("volume_down", None))

    def _raise_if_needed(self, method_name: str) -> None:
        if self.raise_on == method_name:
            raise RuntimeError(f"boom:{method_name}")


class FakeFeedbackOutput:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def show_playing(self) -> None:
        return None

    def show_paused(self) -> None:
        return None

    def show_error(self, reason: str) -> None:
        self.errors.append(reason)


class FakeConfigRepository:
    def __init__(self, targets: dict[str, PlaybackTarget] | None = None) -> None:
        self._targets = targets or {}
        self.requested_card_ids: list[str] = []

    def find_playback_target(self, card_id: str) -> PlaybackTarget | None:
        self.requested_card_ids.append(card_id)
        return self._targets.get(card_id)


def test_known_nfc_card_resolves_to_expected_spotify_context() -> None:
    bus = EventBus()
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    target = PlaybackTarget(uri="spotify:playlist:123", name="Sample")
    config = FakeConfigRepository({"card-1": target})
    controller = PlayerController(bus, spotify, config, feedback)

    controller.register_handlers()
    bus.publish(NfcCardDetected("card-1"))

    assert config.requested_card_ids == ["card-1"]
    assert spotify.calls == [("play_context", target)]
    assert feedback.errors == []


def test_same_playback_target_is_not_started_twice() -> None:
    target = PlaybackTarget(uri="spotify:playlist:a")
    config = FakeConfigRepository({"A": target})
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    bus = EventBus()
    controller = PlayerController(bus, spotify, config, feedback)

    controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))
    controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))

    assert config.requested_card_ids == ["A", "A"]
    assert spotify.calls == [("play_context", target)]
    assert feedback.errors == []


def test_different_playback_target_starts_new_playback() -> None:
    target_a = PlaybackTarget(uri="spotify:playlist:a")
    target_b = PlaybackTarget(uri="spotify:playlist:b")
    config = FakeConfigRepository(
        {
            "A": target_a,
            "B": target_b,
        }
    )
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    bus = EventBus()
    controller = PlayerController(bus, spotify, config, feedback)

    controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))
    controller.on_nfc_card_detected(NfcCardDetected(card_id="B"))

    assert spotify.calls == [
        ("play_context", target_a),
        ("play_context", target_b),
    ]
    assert feedback.errors == []


def test_unknown_card_does_not_replace_current_playback_target() -> None:
    target_a = PlaybackTarget(uri="spotify:playlist:a")
    config = FakeConfigRepository({"A": target_a})
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    bus = EventBus()
    controller = PlayerController(bus, spotify, config, feedback)

    controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))
    controller.on_nfc_card_detected(NfcCardDetected(card_id="UNKNOWN"))
    controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))

    assert spotify.calls == [("play_context", target_a)]
    assert feedback.errors == ["Unknown card: UNKNOWN"]


def test_failed_playback_is_not_remembered_as_current_target() -> None:
    target = PlaybackTarget(uri="spotify:playlist:a")
    config = FakeConfigRepository({"A": target})
    spotify = FakeSpotifyPlayer()
    spotify.raise_on = "play_context"
    feedback = FakeFeedbackOutput()
    bus = EventBus()
    controller = PlayerController(bus, spotify, config, feedback)

    with pytest.raises(RuntimeError, match="boom:play_context"):
        controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))

    spotify.raise_on = None
    controller.on_nfc_card_detected(NfcCardDetected(card_id="A"))

    assert spotify.calls == [("play_context", target)]


def test_unknown_nfc_card_does_not_call_spotify_and_triggers_feedback() -> None:
    bus = EventBus()
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    config = FakeConfigRepository({})
    controller = PlayerController(bus, spotify, config, feedback)

    controller.register_handlers()
    bus.publish(NfcCardDetected("unknown-card"))

    assert config.requested_card_ids == ["unknown-card"]
    assert spotify.calls == []
    assert feedback.errors == ["Unknown card: unknown-card"]


@pytest.mark.parametrize(
    ("event", "expected_method"),
    [
        (PlayPausePressed, "toggle_play_pause"),
        (NextTrackPressed, "next_track"),
        (PreviousTrackPressed, "previous_track"),
        (VolumeUpPressed, "volume_up"),
        (VolumeDownPressed, "volume_down"),
    ],
)
def test_button_events_call_expected_spotify_methods(
    event: type[object],
    expected_method: str,
) -> None:
    bus = EventBus()
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    config = FakeConfigRepository({})
    controller = PlayerController(bus, spotify, config, feedback)

    controller.register_handlers()
    bus.publish(event())

    assert spotify.calls == [(expected_method, None)]


def test_repository_exceptions_propagate() -> None:
    bus = EventBus()
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()

    class ExplodingConfigRepository(FakeConfigRepository):
        def find_playback_target(self, card_id: str) -> PlaybackTarget | None:
            raise RuntimeError(f"boom:{card_id}")

    controller = PlayerController(
        bus,
        spotify,
        ExplodingConfigRepository(),
        feedback,
    )
    controller.register_handlers()

    with pytest.raises(RuntimeError, match="boom:card-1"):
        bus.publish(NfcCardDetected("card-1"))


def test_service_port_exceptions_propagate() -> None:
    bus = EventBus()
    spotify = FakeSpotifyPlayer()
    spotify.raise_on = "play_context"
    feedback = FakeFeedbackOutput()
    config = FakeConfigRepository(
        {
            "card-1": PlaybackTarget(
                uri="spotify:playlist:123",
            )
        }
    )
    controller = PlayerController(bus, spotify, config, feedback)

    controller.register_handlers()

    with pytest.raises(RuntimeError, match="boom:play_context"):
        bus.publish(NfcCardDetected("card-1"))


def test_register_handlers_subscribes_controller_to_event_bus() -> None:
    bus = EventBus()
    spotify = FakeSpotifyPlayer()
    feedback = FakeFeedbackOutput()
    config = FakeConfigRepository({})
    controller = PlayerController(bus, spotify, config, feedback)

    controller.register_handlers()
    controller.register_handlers()
    bus.publish(PlayPausePressed())

    assert spotify.calls == [("toggle_play_pause", None)]