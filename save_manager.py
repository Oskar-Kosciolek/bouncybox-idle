import json
import os
import time
from dataclasses import asdict, fields
from pathlib import Path

from game_state import GameState

SAVE_VERSION = 1

# Ścieżka liczona od pliku gry, nie od katalogu roboczego — inaczej
# uruchomienie gry z innego folderu zaczyna nową grę obok starego zapisu.
SAVE_PATH = Path(__file__).resolve().parent / "save.json"

_FIELD_NAMES = {f.name for f in fields(GameState)}


def save_game(state: GameState, path: Path = SAVE_PATH) -> bool:
    """Zapisuje stan gry. Zwraca False, gdy zapis się nie powiódł.

    Zapis idzie przez plik tymczasowy, a dopiero os.replace podmienia właściwy.
    Zapis w miejscu obcina plik zanim wpisze nową treść, więc przerwanie w tym
    momencie (brak miejsca, zamknięcie systemu) kasuje cały postęp gracza.
    """
    # Stempel czasu należy do zapisu, nie do rozgrywki — to zapis jest tym,
    # od czego liczy się nieobecność.
    state.last_played_at = time.time()

    data = {"version": SAVE_VERSION, **asdict(state)}
    data["achievements_unlocked"] = sorted(state.achievements_unlocked)

    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
        return True
    except (OSError, TypeError, ValueError) as e:
        print(f"Nie udalo sie zapisac gry: {e}")
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def load_game(path: Path = SAVE_PATH) -> GameState | None:
    """Wczytuje stan gry. Zwraca None, gdy zapisu nie ma lub jest nieczytelny.

    Nieznane pola pomijamy, brakujące dostają wartość domyślną z GameState —
    dzięki temu dodanie ani usunięcie pola nie unieważnia zapisów graczy.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as e:
        print(f"Nie udalo sie odczytac zapisu: {e}")
        return None

    try:
        data = json.loads(raw)
        known = {k: v for k, v in data.items() if k in _FIELD_NAMES}
        known["achievements_unlocked"] = set(data.get("achievements_unlocked", []))
        return GameState(**known)
    except Exception as e:
        print(f"Zapis uszkodzony ({e}) — odkladam go obok jako .corrupt")
        _preserve_corrupt(path, raw)
        return None


def _preserve_corrupt(path: Path, raw: str) -> None:
    """Odkłada nieczytelny zapis obok, zanim autozapis go nadpisze.

    Uszkodzony plik bywa jedyną kopią postępu — czasem da się go uratować ręcznie.
    """
    try:
        path.with_name(path.name + ".corrupt").write_text(raw, encoding="utf-8")
    except OSError as e:
        print(f"Nie udalo sie odlozyc uszkodzonego zapisu: {e}")


def delete_save(path: Path = SAVE_PATH) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
