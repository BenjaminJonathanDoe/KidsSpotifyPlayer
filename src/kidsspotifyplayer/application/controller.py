from __future__ import annotations

from kidsspotifyplayer.domain.events import (
    NfcCardDetected,
    NextTrackPressed,
    PlayPausePressed,
    PreviousTrackPressed,
    VolumeDownPressed,
    VolumeUpPressed,
)
from kidsspotifyplayer.event_bus import EventBus
from kidsspotifyplayer.ports import (
    ConfigRepository,
    FeedbackOutput,
    SpotifyPlayer,
)


class PlayerController:
    """Translate domain events into service-port calls."""

    def __init__(
        self,
        event_bus: EventBus,
        spotify_player: SpotifyPlayer,
        config_repository: ConfigRepository,
        feedback_output: FeedbackOutput,
    ) -> None:
        self._event_bus = event_bus
        self._spotify_player = spotify_player
        self._config_repository = config_repository
        self._feedback_output = feedback_output

    def register_handlers(self) -> None:
        self._event_bus.subscribe(NfcCardDetected, self.on_nfc_card_detected)
        self._event_bus.subscribe(PlayPausePressed, self.on_play_pause_pressed)
        self._event_bus.subscribe(NextTrackPressed, self.on_next_track_pressed)
        self._event_bus.subscribe(PreviousTrackPressed, self.on_previous_track_pressed)
        self._event_bus.subscribe(VolumeUpPressed, self.on_volume_up_pressed)
        self._event_bus.subscribe(VolumeDownPressed, self.on_volume_down_pressed)

    def on_nfc_card_detected(self, event: NfcCardDetected) -> None:
        target = self._config_repository.find_playback_target(event.card_id)
        if target is None:
            self._feedback_output.show_error(f"Unknown card: {event.card_id}")
            return

        self._spotify_player.play_context(target)

    def on_play_pause_pressed(self, event: PlayPausePressed) -> None:
        del event
        self._spotify_player.toggle_play_pause()

    def on_next_track_pressed(self, event: NextTrackPressed) -> None:
        del event
        self._spotify_player.next_track()

    def on_previous_track_pressed(self, event: PreviousTrackPressed) -> None:
        del event
        self._spotify_player.previous_track()

    def on_volume_up_pressed(self, event: VolumeUpPressed) -> None:
        del event
        self._spotify_player.volume_up()

    def on_volume_down_pressed(self, event: VolumeDownPressed) -> None:
        del event
        self._spotify_player.volume_down()
