from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kidsspotifyplayer.domain.models import PlaybackTarget
from kidsspotifyplayer.ports import ConfigRepository


class JSONConfigRepository(ConfigRepository):
    """Read-only configuration repository backed by a JSON file."""

    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)
        self._targets = self._load_targets(self._config_path)

    def find_playback_target(self, card_id: str) -> PlaybackTarget | None:
        normalized_card_id = self._normalize_card_id(card_id)
        return self._targets.get(normalized_card_id)

    def _load_targets(self, config_path: Path) -> dict[str, PlaybackTarget]:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with config_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in configuration file: {config_path}") from exc

        if not isinstance(payload, dict):
            raise ValueError("Configuration root must be an object")

        if "cards" not in payload:
            raise ValueError("Configuration must define a 'cards' object")

        cards = payload["cards"]
        if not isinstance(cards, dict):
            raise ValueError("Configuration 'cards' value must be an object")

        targets: dict[str, PlaybackTarget] = {}
        for raw_card_id, raw_entry in cards.items():
            card_id = self._normalize_card_id(raw_card_id)
            if not card_id:
                raise ValueError("Configuration card ID must be a non-empty string")

            if not isinstance(raw_entry, dict):
                raise ValueError(f"Configuration card entry for '{raw_card_id}' must be an object")

            if "uri" not in raw_entry:
                raise ValueError(f"Configuration card entry for '{raw_card_id}' is missing 'uri'")

            uri = raw_entry["uri"]
            if not isinstance(uri, str) or not uri.strip():
                raise ValueError(f"Configuration card entry for '{raw_card_id}' has an invalid 'uri'")

            targets[card_id] = PlaybackTarget(uri=uri.strip())

        return targets

    def _normalize_card_id(self, card_id: Any) -> str:
        if not isinstance(card_id, str):
            raise ValueError("Configuration card ID must be a non-empty string")
        return card_id.strip().upper()
