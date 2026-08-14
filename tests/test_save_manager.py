import json

import save_manager
from game_state import GameState
from save_manager import SAVE_VERSION, delete_save, load_game, save_game


def test_roundtrip_restores_progress(tmp_path):
    path = tmp_path / "save.json"
    state = GameState(coins=1234.5, wave=7, rings_destroyed=42)
    state.achievements_unlocked = {"wave_5", "first_ring"}

    save_game(state, path)
    loaded = load_game(path)

    assert loaded.coins == 1234.5
    assert loaded.wave == 7
    assert loaded.rings_destroyed == 42
    assert loaded.achievements_unlocked == {"wave_5", "first_ring"}


def test_save_records_version(tmp_path):
    """Wersja musi być zapisywana zanim będzie potrzebna — inaczej zapisy
    sprzed wersjonowania są nie do odróżnienia od tych po nim."""
    path = tmp_path / "save.json"

    save_game(GameState(), path)

    assert json.loads(path.read_text(encoding="utf-8"))["version"] == SAVE_VERSION


def test_save_with_removed_field_still_loads(tmp_path):
    """Pole usunięte z GameState w nowszej wersji gry nie może wysadzać
    wczytywania — dotąd GameState(**data) rzucał TypeError i tracił postęp."""
    path = tmp_path / "save.json"
    save_game(GameState(coins=500.0), path)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["upgrade_ktorego_juz_nie_ma"] = 3
    path.write_text(json.dumps(data), encoding="utf-8")

    assert load_game(path).coins == 500.0


def test_save_without_new_field_gets_default(tmp_path):
    """Stary zapis nie zna pól dodanych później — mają przyjąć wartość domyślną."""
    path = tmp_path / "save.json"
    save_game(GameState(coins=500.0), path)

    data = json.loads(path.read_text(encoding="utf-8"))
    del data["prestige_crystals"]
    path.write_text(json.dumps(data), encoding="utf-8")

    loaded = load_game(path)

    assert loaded.coins == 500.0
    assert loaded.prestige_crystals == GameState().prestige_crystals


def test_corrupt_save_is_preserved_not_silently_dropped(tmp_path):
    """Uszkodzony plik to często jedyna kopia postępu gracza. Zamiast go
    nadpisać przy najbliższym autozapisie, odkładamy go obok."""
    path = tmp_path / "save.json"
    path.write_text("{to nie jest poprawny json", encoding="utf-8")

    assert load_game(path) is None
    assert (tmp_path / "save.json.corrupt").read_text(encoding="utf-8") == \
        "{to nie jest poprawny json"


def test_failed_write_leaves_previous_save_intact(tmp_path, monkeypatch):
    """Zapis w miejscu obcina plik zanim wpisze nową treść — przerwanie w tym
    momencie kasuje postęp. Zapis ma iść przez plik tymczasowy."""
    path = tmp_path / "save.json"
    save_game(GameState(coins=100.0), path)

    def boom(*args, **kwargs):
        raise OSError("dysk pelny")

    monkeypatch.setattr(save_manager.json, "dump", boom)

    assert save_game(GameState(coins=999.0), path) is False
    assert load_game(path).coins == 100.0


def test_missing_save_returns_none(tmp_path):
    assert load_game(tmp_path / "nie_ma_takiego.json") is None


def test_delete_save_removes_file(tmp_path):
    path = tmp_path / "save.json"
    save_game(GameState(), path)

    delete_save(path)

    assert not path.exists()


def test_default_save_path_is_next_to_the_game(tmp_path, monkeypatch):
    """Ścieżka względna zapisywała do katalogu roboczego — uruchomienie gry
    z innego folderu gubiło postęp."""
    monkeypatch.chdir(tmp_path)

    assert save_manager.SAVE_PATH.parent == save_manager.Path(
        save_manager.__file__).resolve().parent
