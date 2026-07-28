from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.domain.events import (
    ApplicationReady,
    ApplicationStarted,
    ApplicationStopping,
    ConfigurationFailed,
    HardwareFailed,
    NetworkAvailable,
    NetworkUnavailable,
    NfcCardDetected,
    NfcCardRemoved,
    NextTrackPressed,
    PlaybackFailed,
    PlaybackPaused,
    PlaybackStarted,
    PlayPausePressed,
    PreviousTrackPressed,
    ShutdownRequested,
    SpotifyAvailable,
    SpotifyUnavailable,
    TrackChanged,
    VolumeChanged,
    VolumeDownPressed,
    VolumeUpPressed,
)


def test_input_events_are_immutable() -> None:
    detected = NfcCardDetected(card_id="card-123")
    removed = NfcCardRemoved(card_id="card-123")

    assert detected.card_id == "card-123"
    assert removed.card_id == "card-123"

    with pytest.raises(FrozenInstanceError):
        detected.card_id = "card-999"


def test_lifecycle_and_playback_events_store_values() -> None:
    started = ApplicationStarted()
    ready = ApplicationReady()
    stopping = ApplicationStopping()
    playback_started = PlaybackStarted(context_uri="spotify:album:1", track_name="Song")
    playback_paused = PlaybackPaused()
    track_changed = TrackChanged(track_name="Song", artist_name="Artist")
    volume_changed = VolumeChanged(volume_percent=42)
    playback_failed = PlaybackFailed(reason="network", recoverable=True)

    assert isinstance(started, ApplicationStarted)
    assert isinstance(ready, ApplicationReady)
    assert isinstance(stopping, ApplicationStopping)
    assert playback_started.context_uri == "spotify:album:1"
    assert playback_started.track_name == "Song"
    assert isinstance(playback_paused, PlaybackPaused)
    assert track_changed.artist_name == "Artist"
    assert volume_changed.volume_percent == 42
    assert playback_failed.recoverable is True


def test_connectivity_and_failure_events_are_immutable() -> None:
    available = NetworkAvailable()
    unavailable = NetworkUnavailable()
    spotify_available = SpotifyAvailable()
    spotify_unavailable = SpotifyUnavailable()
    config_failed = ConfigurationFailed(reason="missing config")
    hardware_failed = HardwareFailed(component="nfc", reason="offline", recoverable=False)

    assert isinstance(available, NetworkAvailable)
    assert isinstance(unavailable, NetworkUnavailable)
    assert isinstance(spotify_available, SpotifyAvailable)
    assert isinstance(spotify_unavailable, SpotifyUnavailable)
    assert config_failed.reason == "missing config"
    assert hardware_failed.component == "nfc"
    assert hardware_failed.recoverable is False


def test_button_and_shutdown_events_are_simple_empty_events() -> None:
    assert isinstance(PlayPausePressed(), PlayPausePressed)
    assert isinstance(NextTrackPressed(), NextTrackPressed)
    assert isinstance(PreviousTrackPressed(), PreviousTrackPressed)
    assert isinstance(VolumeUpPressed(), VolumeUpPressed)
    assert isinstance(VolumeDownPressed(), VolumeDownPressed)
    assert isinstance(ShutdownRequested(), ShutdownRequested)
