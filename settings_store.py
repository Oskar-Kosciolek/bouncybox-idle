import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Config

# Ścieżka liczona od pliku gry, nie od katalogu roboczego — tak samo jak
# SAVE_PATH, żeby uruchomienie z innego folderu nie gubiło ustawień.
#
# Osobny plik, a nie save.json: RESET WSZYSTKIEGO kasuje zapis gry, a głośność
# nie jest postępem tylko preferencją. Po wyczyszczeniu gry muzyka nie ma
# wracać na domyślny regulator.
SETTINGS_PATH = Path(__file__).resolve().parent / "settings.json"

# Pola Config należące do gracza, nie do strojenia balansu: (nazwa, min, max).
# Config ma ich ~30, ale zamrożenie w pliku reszty oznaczałoby, że każda
# przyszła zmiana balansu omija każdego, kto raz ruszył suwak.
USER_SETTINGS: dict[str, tuple[float, float]] = {
    "sound_volume": (0.0, 1.0),
    "music_volume": (0.0, 1.0),
}


def save_settings(config: "Config", path: Path = SETTINGS_PATH) -> bool:
    """Zapisuje ustawienia gracza. Zwraca False, gdy się nie udało.

    Bez pliku tymczasowego, w odróżnieniu od zapisu gry: tu najgorszym
    skutkiem uszkodzenia jest powrót głośności do domyślnej, a nie utrata
    godzin rozgrywki.
    """
    data = {name: getattr(config, name) for name in USER_SETTINGS}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError as e:
        print(f"Nie udalo sie zapisac ustawien: {e}")
        return False


def load_settings(config: "Config", path: Path = SETTINGS_PATH) -> None:
    """Nakłada zapisane ustawienia na config. Milczy, gdy pliku nie ma.

    Każde pole osobno: jedna zła wartość zostawia domyślną tylko dla siebie,
    zamiast wywracać cały plik. Brak ustawień nie może przerwać startu gry.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except (OSError, ValueError) as e:
        print(f"Ustawienia nieczytelne ({e}) — zostaja domyslne")
        return

    if not isinstance(data, dict):
        return

    for name, (low, high) in USER_SETTINGS.items():
        if name not in data:
            continue
        value = data[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        setattr(config, name, min(high, max(low, float(value))))


def delete_settings(path: Path = SETTINGS_PATH) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
