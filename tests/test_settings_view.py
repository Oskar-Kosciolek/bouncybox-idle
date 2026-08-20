import pygame

from confirm import ConfirmedAction
from config import Config
from ui.settings_view import SettingsView

pygame.font.init()

WIN_W, WIN_H = 520, 520


def _view() -> tuple[SettingsView, ConfirmedAction, list[int]]:
    fired: list[int] = []
    confirm = ConfirmedAction(window_seconds=3.0)
    view = SettingsView(confirm)
    view.draw(pygame.Surface((700, WIN_H)),
              pygame.font.SysFont("segoeui", 13), Config(), 100.0,
              WIN_W, WIN_H)
    return view, confirm, fired


def _click(view, pos, on_reset, now=100.0) -> None:
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                         pos=pos),
                      Config(), on_reset, now, WIN_W, WIN_H)


def test_the_first_click_on_reset_only_arms_it():
    view, _, fired = _view()

    _click(view, view.reset_btn_rect().center, lambda: fired.append(1))

    assert fired == []


def test_a_second_click_inside_the_window_resets():
    view, _, fired = _view()

    _click(view, view.reset_btn_rect().center, lambda: fired.append(1), now=100.0)
    _click(view, view.reset_btn_rect().center, lambda: fired.append(1), now=101.0)

    assert fired == [1]


def test_a_second_click_after_the_window_only_arms_again():
    view, _, fired = _view()

    _click(view, view.reset_btn_rect().center, lambda: fired.append(1), now=100.0)
    _click(view, view.reset_btn_rect().center, lambda: fired.append(1), now=110.0)

    assert fired == []


def test_the_button_label_asks_for_confirmation_once_armed():
    view, _, fired = _view()

    assert view.reset_btn_label(now=100.0) == "RESET WSZYSTKIEGO"

    _click(view, view.reset_btn_rect().center, lambda: fired.append(1))

    assert view.reset_btn_label(now=100.5) == "NA PEWNO? (klik znow)"


def test_the_reset_button_does_not_scroll_away_with_the_sliders():
    """Suwaków jest 18 — przycisk przewijany razem z nimi byłby poza
    ekranem dokładnie wtedy, gdy gracz go szuka."""
    view, _, _ = _view()
    before = view.reset_btn_rect()

    view.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-20),
                      Config(), lambda: None, 100.0, WIN_W, WIN_H)

    assert view.reset_btn_rect() == before


def test_clicking_the_reset_button_does_not_drag_a_slider_underneath_it():
    """Suwaki przewijają się pod stopką. Bez wyłączenia stopki z trafiania
    jeden klik i kasuje postęp, i przestawia balans."""
    view, _, fired = _view()
    config = Config()
    # Przewiń tak, żeby któryś suwak wylądował pod przyciskiem.
    for _ in range(20):
        view.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1),
                          config, lambda: None, 100.0, WIN_W, WIN_H)
    before = [getattr(config, f[1]) for f in _sliders()]

    view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                           pos=view.reset_btn_rect().center),
        config, lambda: fired.append(1), 100.0, WIN_W, WIN_H)

    assert [getattr(config, f[1]) for f in _sliders()] == before


def _sliders():
    from ui.settings_view import _SLIDERS
    return _SLIDERS
