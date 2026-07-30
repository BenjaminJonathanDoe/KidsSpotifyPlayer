from __future__ import annotations

from pathlib import Path

from kidsspotifyplayer.adapters.config.json_config_repository import JSONConfigRepository
from kidsspotifyplayer.application.controller import PlayerController
from kidsspotifyplayer.event_bus import EventBus
from kidsspotifyplayer.input import InputCoordinator
from kidsspotifyplayer.ports import FeedbackOutput, SpotifyPlayer


class Application:
    """Compose the application and own its synchronous lifecycle."""

    def __init__(
        self,
        config_path: str | Path,
        spotify_player: SpotifyPlayer,
        feedback_output: FeedbackOutput,
    ) -> None:
        self._config_path = Path(config_path)
        self.event_bus = EventBus()
        self.input_coordinator = InputCoordinator(self.event_bus)
        self.config_repository = JSONConfigRepository(self._config_path)
        self.spotify_player = spotify_player
        self.feedback_output = feedback_output
        self.controller = PlayerController(
            self.event_bus,
            self.spotify_player,
            self.config_repository,
            self.feedback_output,
        )
        self.controller.register_handlers()

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None
