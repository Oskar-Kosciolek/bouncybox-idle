import re
from pathlib import Path

import pygame

from confirm import ConfirmedAction
from constants import PANEL_W
from ui.game_view import GameView

pygame.font.init()

WIN_W, WIN_H = 520, 520


def _view() -> tuple[GameView, ConfirmedAction, list[str]]:
    """Widok z ustawionym rect (rysowanie liczy geometrię) i listą zdarzeń."""
    log: list[str] = []
    confirm = ConfirmedAction(window_seconds=3.0)
    view = GameView(confirm)
    view.draw_controls(pygame.Surface((700, WIN_H)),
                       pygame.font.SysFont("segoeui", 13),
                       100.0, WIN_W, WIN_H)
    return view, confirm, log


def _click(view, pos, log, now=100.0) -> None:
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                         pos=pos),
                      lambda: log.append("save"), lambda: log.append("reset"),
                      now, WIN_W, WIN_H)


def _readme_shortcut_keys() -> list[str]:
    readme = (Path(__file__).resolve().parent.parent / "README.md"
              ).read_text(encoding="utf-8")
    return re.findall(r"^\| `(\w+)` \|", readme, re.M)


# ----------------------------------------------------------------------
# Zapis
# ----------------------------------------------------------------------

def test_the_save_button_saves_immediately():
    """Zapis niczego nie niszczy, więc nie ma czego potwierdzać."""
    view, _, log = _view()

    _click(view, view.save_btn_rect().center, log)

    assert log == ["save"]


def test_a_click_between_the_buttons_does_nothing():
    view, _, log = _view()
    middle = (view.save_btn_rect().centerx,
              (view.save_btn_rect().bottom + view.reset_btn_rect().top) // 2)

    _click(view, middle, log)

    assert log == []


# ----------------------------------------------------------------------
# Reset
# ----------------------------------------------------------------------

def test_the_reset_button_only_arms_on_the_first_click():
    view, _, log = _view()

    _click(view, view.reset_btn_rect().center, log)

    assert log == []


def test_the_reset_button_fires_on_the_second_click():
    view, _, log = _view()

    _click(view, view.reset_btn_rect().center, log, now=100.0)
    _click(view, view.reset_btn_rect().center, log, now=101.0)

    assert log == ["reset"]


def test_saving_does_not_arm_the_reset():
    """Gdyby zapis dzielił uzbrojenie z resetem, klik ZAPISZ i klik RESET
    kasowałyby grę w dwóch ruchach."""
    view, confirm, log = _view()

    _click(view, view.save_btn_rect().center, log)

    assert confirm.is_armed(now=100.5) is False


def test_the_reset_label_asks_for_confirmation_once_armed():
    view, _, log = _view()

    assert view.reset_btn_label(now=100.0) == "RESET WSZYSTKIEGO"

    _click(view, view.reset_btn_rect().center, log)

    assert view.reset_btn_label(now=100.5) == "NA PEWNO? (klik znow)"


# ----------------------------------------------------------------------
# Układ — przyciski mają być rozdzielone treścią, nie sąsiadować
# ----------------------------------------------------------------------

def test_the_two_buttons_are_separated_by_a_screenful_of_text():
    """Zapis i reset obok siebie to ta sama pułapka co F5 obok F6,
    tyle że myszą."""
    view, _, _ = _view()

    gap = view.reset_btn_rect().top - view.save_btn_rect().bottom

    assert gap >= 150


def test_the_text_does_not_run_under_the_reset_button():
    """Panel ma 300 px przy oknie 520 — treść rosnąca o jedną linię za dużo
    chowa się pod przyciskiem, bez żadnego błędu."""
    view, _, _ = _view()

    assert view.content_bottom() <= view.reset_btn_rect().top


def test_the_buttons_stay_inside_the_panel():
    view, _, _ = _view()

    assert view.rect.contains(view.save_btn_rect())
    assert view.rect.contains(view.reset_btn_rect())


# ----------------------------------------------------------------------
# Treść
# ----------------------------------------------------------------------

def test_the_in_game_controls_list_the_same_keys_as_the_readme():
    """README twierdził, że panel ma sześć zakładek ze Sklepem, długo po tym
    jak Sklep zniknął. Lista klawiszy zestarzeje się tak samo, jeśli jedyną
    kopią prawdy będzie plik, do którego nikt nie zagląda przy zmianie kodu.
    """
    assert [key for key, _ in GameView.CONTROLS] == _readme_shortcut_keys()


def test_every_text_line_fits_the_panel():
    """Dłuższy wiersz wychodzi poza krawędź i jest ucięty w połowie słowa."""
    font = pygame.font.SysFont("segoeui", 13)

    for key, action in GameView.CONTROLS:
        width = font.size(key)[0] + font.size(action)[0]
        assert width < PANEL_W - 20, f"{key} {action}"

    for line in GameView.ABOUT:
        assert font.size(line)[0] < PANEL_W - 20, line


def test_drawing_the_panel_fills_it():
    view, _, _ = _view()
    surface = pygame.Surface((700, WIN_H))

    view.draw_controls(surface, pygame.font.SysFont("segoeui", 13),
                       100.0, WIN_W, WIN_H)

    blank = pygame.Surface((700, WIN_H))
    assert (pygame.image.tobytes(surface, "RGB")
            != pygame.image.tobytes(blank, "RGB"))
