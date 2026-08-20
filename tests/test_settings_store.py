import json

import pytest

from config import Config
from settings_store import (USER_SETTINGS, load_settings, save_settings)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "settings.json"


def test_a_round_trip_restores_both_volumes(path):
    saved = Config()
    saved.sound_volume = 0.8
    saved.music_volume = 0.1
    save_settings(saved, path)

    loaded = Config()
    load_settings(loaded, path)

    assert loaded.sound_volume == 0.8
    assert loaded.music_volume == 0.1


def test_a_missing_file_leaves_the_defaults_alone(path):
    config = Config()
    defaults = (config.sound_volume, config.music_volume)

    load_settings(config, path)

    assert (config.sound_volume, config.music_volume) == defaults


def test_a_corrupt_file_leaves_the_defaults_alone(path):
    """Zapis ustawień nie jest postępem, więc uszkodzony plik ma po cichu
    zniknąć z drogi — inaczej gra nie wstaje przez suwak głośności."""
    path.write_text("{to nie jest json", encoding="utf-8")
    config = Config()
    defaults = (config.sound_volume, config.music_volume)

    load_settings(config, path)

    assert (config.sound_volume, config.music_volume) == defaults


def test_unknown_keys_are_ignored(path):
    """Plik jest edytowalny ręcznie i przeżywa zmiany wersji — nieznany klucz
    nie może wysadzić startu ani wstrzyknąć czegokolwiek w Config."""
    path.write_text(json.dumps({"sound_volume": 0.7, "hole_damage_multiplier": 999}),
                    encoding="utf-8")
    config = Config()

    load_settings(config, path)

    assert config.sound_volume == 0.7
    assert config.hole_damage_multiplier == Config().hole_damage_multiplier


def test_values_outside_the_slider_range_are_clamped(path):
    path.write_text(json.dumps({"sound_volume": 5.0, "music_volume": -3.0}),
                    encoding="utf-8")
    config = Config()

    load_settings(config, path)

    assert config.sound_volume == 1.0
    assert config.music_volume == 0.0


def test_a_non_numeric_value_falls_back_to_the_default(path):
    path.write_text(json.dumps({"sound_volume": "gloszno"}), encoding="utf-8")
    config = Config()

    load_settings(config, path)

    assert config.sound_volume == Config().sound_volume


def test_only_the_user_facing_fields_are_written(path):
    """Plik jest dla gracza. Zrzucenie tam całego Config zamroziłoby też
    18 pokręteł deweloperskich i strojenie balansu przestałoby działać
    dla kogokolwiek, kto raz ruszył suwak."""
    save_settings(Config(), path)

    assert set(json.loads(path.read_text(encoding="utf-8"))) == set(USER_SETTINGS)


def test_saving_into_an_unwritable_path_does_not_raise(tmp_path):
    """Brak zapisu ustawień nie może przerwać rozgrywki."""
    assert save_settings(Config(), tmp_path / "brak" / "settings.json") is False
