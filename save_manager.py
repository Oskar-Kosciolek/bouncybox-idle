import json
import os
from dataclasses import asdict
from game_state import GameState

SAVE_FILE = "save.json"


def save_game(state: GameState) -> None:
    data = asdict(state)
    data["achievements_unlocked"] = list(state.achievements_unlocked)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_game() -> GameState | None:
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["achievements_unlocked"] = set(data["achievements_unlocked"])
        return GameState(**data)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Błąd wczytywania zapisu: {e}")
        return None


def delete_save() -> None:
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
