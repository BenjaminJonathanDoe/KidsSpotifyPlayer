from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NfcCardDetected:
    card_id: str


@dataclass(frozen=True)
class NfcCardRemoved:
    card_id: str


@dataclass(frozen=True)
class PlayPausePressed:
    pass


@dataclass(frozen=True)
class NextTrackPressed:
    pass


@dataclass(frozen=True)
class PreviousTrackPressed:
    pass


@dataclass(frozen=True)
class VolumeUpPressed:
    pass


@dataclass(frozen=True)
class VolumeDownPressed:
    pass


@dataclass(frozen=True)
class ShutdownRequested:
    pass


@dataclass(frozen=True)
class ApplicationStarted:
    pass


@dataclass(frozen=True)
class ApplicationReady:
    pass


@dataclass(frozen=True)
class ApplicationStopping:
    pass


@dataclass(frozen=True)
class PlaybackStarted:
    context_uri: str | None = None
    track_name: str | None = None


@dataclass(frozen=True)
class PlaybackPaused:
    pass


@dataclass(frozen=True)
class TrackChanged:
    track_name: str | None = None
    artist_name: str | None = None


@dataclass(frozen=True)
class VolumeChanged:
    volume_percent: int


@dataclass(frozen=True)
class PlaybackFailed:
    reason: str
    recoverable: bool


@dataclass(frozen=True)
class NetworkAvailable:
    pass


@dataclass(frozen=True)
class NetworkUnavailable:
    pass


@dataclass(frozen=True)
class SpotifyAvailable:
    pass


@dataclass(frozen=True)
class SpotifyUnavailable:
    pass


@dataclass(frozen=True)
class ConfigurationFailed:
    reason: str


@dataclass(frozen=True)
class HardwareFailed:
    component: str
    reason: str
    recoverable: bool
