from __future__ import annotations

from pathlib import Path

from kidsspotifyplayer.adapters.config.json_config_repository import (
    JSONConfigRepository,
)
from kidsspotifyplayer.application.controller import PlayerController
from kidsspotifyplayer.domain.events import NfcCardDetected
from kidsspotifyplayer.event_bus import EventBus
from kidsspotifyplayer.input import InputCoordinator


class ConsoleSpotifyPlayer:
    def play_context(self, target) -> None:
        print(f"PLAY: {target.uri}")

    def toggle_play_pause(self) -> None:
        pass

    def next_track(self) -> None:
        pass

    def previous_track(self) -> None:
        pass

    def volume_up(self) -> None:
        pass

    def volume_down(self) -> None:
        pass


class ConsoleFeedback:
    def show_playing(self) -> None:
        pass

    def show_paused(self) -> None:
        pass

    def show_error(self, reason: str) -> None:
        print(f"ERROR: {reason}")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "scripts" / "simulation_cards.json"

    event_bus = EventBus()
    input_coordinator = InputCoordinator(event_bus)
    config_repository = JSONConfigRepository(config_path)
    spotify_player = ConsoleSpotifyPlayer()
    feedback_output = ConsoleFeedback()

    controller = PlayerController(
        event_bus,
        spotify_player,
        config_repository,
        feedback_output,
    )
    controller.register_handlers()

    print("KidsSpotifyPlayer MVP simulation")
    print("Enter NFC IDs such as 04A10BFF or 0102.")
    print("Enter q to quit.")
    print()

    while True:
        card_id = input("NFC ID: ").strip()

        if card_id.lower() == "q":
            break

        input_coordinator.publish(
            NfcCardDetected(card_id=card_id)
        )


if __name__ == "__main__":
    main()