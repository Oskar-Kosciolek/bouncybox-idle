import re
from pathlib import Path

import pygame

from ui.game_view import GameView

pygame.font.init()


def _readme_shortcut_keys() -> list[str]:
    """Klawisze z tabeli skrótów w README, w kolejności występowania."""
    readme = (Path(__file__).resolve().parent.parent / "README.md"
              ).read_text(encoding="utf-8")
    return re.findall(r"^\| `(\w+)` \|", readme, re.M)


def test_the_in_game_controls_list_the_same_keys_as_the_readme():
    """README twierdził, że panel ma sześć zakładek ze Sklepem, długo po tym
    jak Sklep zniknął. Lista klawiszy zestarzeje się tak samo, jeśli jedyną
    kopią prawdy będzie plik, do którego nikt nie zagląda przy zmianie kodu.
    """
    assert [key for key, _ in GameView.CONTROLS] == _readme_shortcut_keys()


def test_every_control_line_fits_the_panel():
    """Panel ma 180 px. Dłuższy wiersz wychodzi poza krawędź i jest ucięty
    w połowie słowa, bez żadnego błędu."""
    from constants import PANEL_W

    font = pygame.font.SysFont("segoeui", 13)
    for key, action in GameView.CONTROLS:
        width = font.size(f"{key}")[0] + font.size(action)[0]
        assert width < PANEL_W - 20, f"{key} {action}"


def test_drawing_the_controls_panel_fills_it():
    view = GameView()
    surface = pygame.Surface((700, 520))
    font = pygame.font.SysFont("segoeui", 13)

    view.draw_controls(surface, font, 520, 520)

    blank = pygame.Surface((700, 520))
    assert (pygame.image.tobytes(surface, "RGB")
            != pygame.image.tobytes(blank, "RGB"))
