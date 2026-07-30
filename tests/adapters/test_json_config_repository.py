from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kidsspotifyplayer.adapters.config.json_config_repository import JSONConfigRepository
from kidsspotifyplayer.domain.models import PlaybackTarget


def write_config(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_valid_configuration_loads_and_lookups_work(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(
        config_path,
        {
            "cards": {
                "04A1B2C3": {"uri": "spotify:playlist:123456"},
                "04D4E5F6": {"uri": "spotify:album:987654"},
            }
        },
    )

    repository = JSONConfigRepository(config_path)

    assert repository.find_playback_target("04A1B2C3") == PlaybackTarget(
        uri="spotify:playlist:123456"
    )
    assert repository.find_playback_target("04D4E5F6") == PlaybackTarget(
        uri="spotify:album:987654"
    )
    assert repository.find_playback_target("missing") is None


def test_repository_uses_in_memory_data_after_file_changes(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "spotify:playlist:123456"}}})

    repository = JSONConfigRepository(config_path)
    config_path.unlink()

    assert repository.find_playback_target("04A1B2C3") == PlaybackTarget(
        uri="spotify:playlist:123456"
    )


def test_lookup_normalizes_card_ids(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {" 04a1b2c3 ": {"uri": "spotify:playlist:123456"}}})

    repository = JSONConfigRepository(config_path)

    assert repository.find_playback_target("04a1b2c3") == PlaybackTarget(
        uri="spotify:playlist:123456"
    )
    assert repository.find_playback_target(" 04A1B2C3 ") == PlaybackTarget(
        uri="spotify:playlist:123456"
    )


def test_normalization_preserves_separators_and_distinguishes_formats(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(
        config_path,
        {
            "cards": {
                "04:A1:B2:C3": {"uri": "spotify:playlist:123456"},
                "04-A1-B2-C3": {"uri": "spotify:album:987654"},
            }
        },
    )

    repository = JSONConfigRepository(config_path)

    assert repository.find_playback_target("04:a1:b2:c3") == PlaybackTarget(
        uri="spotify:playlist:123456"
    )
    assert repository.find_playback_target("04-a1-b2-c3") == PlaybackTarget(
        uri="spotify:album:987654"
    )
    assert repository.find_playback_target("04A1B2C3") is None


def test_missing_file_fails_construction(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        JSONConfigRepository(tmp_path / "missing.json")


def test_malformed_json_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON"):
        JSONConfigRepository(config_path)


def test_missing_cards_key_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"foo": "bar"})

    with pytest.raises(ValueError, match="cards"):
        JSONConfigRepository(config_path)


def test_non_object_cards_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": []})

    with pytest.raises(ValueError, match="cards"):
        JSONConfigRepository(config_path)


def test_top_level_object_is_required(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, ["not", "an", "object"])

    with pytest.raises(ValueError, match="object"):
        JSONConfigRepository(config_path)


def test_empty_card_id_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"": {"uri": "spotify:playlist:123456"}}})

    with pytest.raises(ValueError, match="card ID"):
        JSONConfigRepository(config_path)


def test_non_object_card_entry_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": "not-an-object"}})

    with pytest.raises(ValueError, match="card entry"):
        JSONConfigRepository(config_path)


def test_missing_uri_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {}}})

    with pytest.raises(ValueError, match="uri"):
        JSONConfigRepository(config_path)


def test_empty_uri_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": "   "}}})

    with pytest.raises(ValueError, match="uri"):
        JSONConfigRepository(config_path)


def test_non_string_uri_fails_construction(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path, {"cards": {"04A1B2C3": {"uri": 42}}})

    with pytest.raises(ValueError, match="uri"):
        JSONConfigRepository(config_path)
