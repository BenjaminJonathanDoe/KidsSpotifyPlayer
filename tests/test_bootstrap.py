from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kidsspotifyplayer.bootstrap import build_runtime


class FakeNfcReader:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class FakeSpotifyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def current_user_devices(self) -> dict[str, Any]:
        self.calls.append(
            (
                "current_user_devices",
                None,
            )
        )

        return {
            "devices": [
                {
                    "name": "KidsSpotifyPlayer",
                    "id": "device-123",
                }
            ]
        }

    def start_playback(
        self,
        *,
        device_id: str,
        context_uri: str | None = None,
    ) -> None:
        return None

    def pause_playback(
        self,
        *,
        device_id: str,
    ) -> None:
        return None

    def next_track(
        self,
        *,
        device_id: str,
    ) -> None:
        return None

    def previous_track(
        self,
        *,
        device_id: str,
    ) -> None:
        return None

    def current_playback(
        self,
    ) -> dict[str, object] | None:
        return None

    def volume(
        self,
        volume_percent: int,
        *,
        device_id: str,
    ) -> None:
        return None


class FakeFeedbackOutput:
    def show_playing(self) -> None:
        return None

    def show_paused(self) -> None:
        return None

    def show_error(self, reason: str) -> None:
        del reason


def test_build_runtime_wires_core_components(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"cards": {}}',
        encoding="utf-8",
    )

    nfc_reader = FakeNfcReader()
    spotify_client = FakeSpotifyClient()
    feedback_output = FakeFeedbackOutput()

    runtime = build_runtime(
        config_path=config_path,
        nfc_reader=nfc_reader,
        spotify_client=spotify_client,
        feedback_output=feedback_output,
        spotify_device_name="KidsSpotifyPlayer",
    )

    assert runtime["event_bus"] is not None
    assert runtime["input_coordinator"] is not None
    assert runtime["config_repository"] is not None
    assert runtime["spotify_player"] is not None
    assert runtime["controller"] is not None

    assert runtime["nfc_reader"] is nfc_reader
    assert runtime["feedback_output"] is feedback_output

    assert nfc_reader.started is True

    assert spotify_client.calls == [
        (
            "current_user_devices",
            None,
        )
    ]


def test_build_runtime_can_use_explicit_device_id_without_discovery(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"cards": {}}',
        encoding="utf-8",
    )

    nfc_reader = FakeNfcReader()
    spotify_client = FakeSpotifyClient()

    runtime = build_runtime(
        config_path=config_path,
        nfc_reader=nfc_reader,
        spotify_client=spotify_client,
        feedback_output=FakeFeedbackOutput(),
        device_id="explicit-device-id",
    )

    assert runtime["spotify_player"] is not None

    assert spotify_client.calls == []