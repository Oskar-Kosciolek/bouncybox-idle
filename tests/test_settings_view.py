import pygame

from config import Config
from settings_store import USER_SETTINGS
from ui.settings_view import _HDR_H, _SECTIONS, _SLIDERS, SettingsView

pygame.font.init()

WIN_W, WIN_H = 520, 520


def _view() -> tuple[SettingsView, Config, list[int]]:
    saves: list[int] = []
    view = SettingsView()
    view.draw(pygame.Surface((700, WIN_H)),
              pygame.font.SysFont("segoeui", 13), Config(), WIN_W, WIN_H)
    return view, Config(), saves


def _send(view, event, config, saves) -> None:
    view.handle_event(event, config, lambda: saves.append(1), WIN_W, WIN_H)


# ----------------------------------------------------------------------
# Zapis ustawień
# ----------------------------------------------------------------------

def test_one_drag_writes_the_file_once():
    """Przeciąganie sypie zdarzeniami co klatkę. Zapis na MOUSEMOTION to
    ~60 zapisów pliku na sekundę przez cały czas trzymania suwaka."""
    view, config, saves = _view()
    bar = view._bar_rect(0)

    _send(view, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=bar.center), config, saves)
    for x in range(bar.x, bar.right, 4):
        _send(view, pygame.event.Event(pygame.MOUSEMOTION, pos=(x, bar.centery)),
              config, saves)
    _send(view, pygame.event.Event(pygame.MOUSEBUTTONUP, button=1,
                                   pos=bar.midright), config, saves)

    assert saves == [1]


def test_a_drag_still_changes_the_value():
    view, config, saves = _view()
    bar = view._bar_rect(0)

    _send(view, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=bar.midleft), config, saves)
    _send(view, pygame.event.Event(pygame.MOUSEBUTTONUP, button=1,
                                   pos=bar.midleft), config, saves)

    assert config.sound_volume == 0.0


def test_releasing_the_mouse_without_dragging_writes_nothing():
    """Puszczenie przycisku po kliknięciu gdziekolwiek indziej nie jest
    zmianą ustawień."""
    view, config, saves = _view()

    _send(view, pygame.event.Event(pygame.MOUSEBUTTONUP, button=1,
                                   pos=(0, 0)), config, saves)

    assert saves == []


def test_scrolling_writes_nothing():
    view, config, saves = _view()

    _send(view, pygame.event.Event(pygame.MOUSEWHEEL, y=-3), config, saves)

    assert saves == []


# ----------------------------------------------------------------------
# Sekcje
# ----------------------------------------------------------------------

def test_every_persisted_setting_has_a_slider():
    """Zapisywanie pola, którego gracz nie może ruszyć, zamraża je na
    zawsze w pliku — i żadna przyszła zmiana domyślnej wartości go nie
    dosięgnie."""
    fields = {field for _, field, *_ in _SLIDERS}

    assert set(USER_SETTINGS) <= fields


def test_the_persisted_settings_come_first_under_their_own_header():
    """Głośność to ustawienie gracza. Zakopana między 'Dziura x obrazen'
    a 'Szansa mystery' jest nie do znalezienia."""
    first = {field for _, field, *_ in _SLIDERS[:len(USER_SETTINGS)]}

    assert first == set(USER_SETTINGS)
    assert 0 in _SECTIONS
    assert len(USER_SETTINGS) in _SECTIONS


def test_no_dev_slider_is_persisted():
    """Zamrożenie pokrętła balansu w pliku gracza wyłącza go ze strojenia."""
    dev = {field for _, field, *_ in _SLIDERS[len(USER_SETTINGS):]}

    assert dev.isdisjoint(USER_SETTINGS)


def test_a_section_header_pushes_the_rows_below_it_down():
    """Nagłówek zajmuje miejsce. Gdyby go nie doliczać do pozycji wierszy,
    pierwszy suwak sekcji rysowałby się na jej tytule — a trafianie
    w suwaki liczyłoby się z tego samego, błędnego wzoru."""
    view, _, _ = _view()

    inside_section = view._row_y(1) - view._row_y(0)
    across_section = view._row_y(2) - view._row_y(1)

    assert across_section - inside_section == _HDR_H
