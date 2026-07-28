from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Event:
    """Base type for immutable domain events."""


@dataclass(frozen=True, slots=True)
class NfcCardDetected(Event):
    card_id: str


@dataclass(frozen=True, slots=True)
class NfcCardRemoved(Event):
    card_id: str


@dataclass(frozen=True, slots=True)
class PlayPausePressed(Event):
    pass


@dataclass(frozen=True, slots=True)
class NextTrackPressed(Event):
    pass


@dataclass(frozen=True, slots=True)
class PreviousTrackPressed(Event):
    pass


@dataclass(frozen=True, slots=True)
class VolumeUpPressed(Event):
    pass


@dataclass(frozen=True, slots=True)
class VolumeDownPressed(Event):
    pass


@dataclass(frozen=True, slots=True)
class ShutdownRequested(Event):
    pass


@dataclass(frozen=True, slots=True)
class ApplicationStarted(Event):
    pass


@dataclass(frozen=True, slots=True)
class ApplicationReady(Event):
    pass


@dataclass(frozen=True, slots=True)
class ApplicationStopping(Event):
    pass


@dataclass(frozen=True, slots=True)
class PlaybackStarted(Event):
    context_uri: str | None = None
    track_name: str | None = None


@dataclass(frozen=True, slots=True)
class PlaybackPaused(Event):
    pass


@dataclass(frozen=True, slots=True)
class TrackChanged(Event):
    track_name: str | None = None
    artist_name: str | None = None


@dataclass(frozen=True, slots=True)
class VolumeChanged(Event):
    volume_percent: int


@dataclass(frozen=True, slots=True)
class PlaybackFailed(Event):
    reason: str
    recoverable: bool


@dataclass(frozen=True, slots=True)
class NetworkAvailable(Event):
    pass


@dataclass(frozen=True, slots=True)
class NetworkUnavailable(Event):
    pass


@dataclass(frozen=True, slots=True)
class SpotifyAvailable(Event):
    pass


@dataclass(frozen=True, slots=True)
class SpotifyUnavailable(Event):
    pass


@dataclass(frozen=True, slots=True)
class ConfigurationFailed(Event):
    reason: str


@dataclass(frozen=True, slots=True)
class HardwareFailed(Event):
    component: str
    reason: str
    recoverable: bool
