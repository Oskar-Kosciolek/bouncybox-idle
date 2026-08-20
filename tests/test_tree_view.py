import pygame

from game_state import GameState
from ui.tree_view import (_BRANCH_ORDER, _COL_BG, _COL_DETAIL_BG,
                          TreeView)
from upgrade_tree import UPGRADES

pygame.font.init()

WIN_W, WIN_H = 520, 520          # domyślne okno gry: 700x520 minus panel


def _view(state: GameState) -> tuple[TreeView, pygame.Surface, pygame.font.Font]:
    return (TreeView(state, UPGRADES),
            pygame.Surface((700, WIN_H)),
            pygame.font.SysFont("segoeui", 13))


def _rows(branch: str) -> int:
    return len([u for u in UPGRADES if u.branch == branch])


def test_clicking_a_node_buys_one_level():
    state = GameState(coins=10_000.0)
    view, _, _ = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)

    pos = view.node_centre(0, 0)
    bought = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos),
        WIN_W, WIN_H)

    assert bought is True
    assert state.upgrade_ball_speed == 1


def test_clicking_between_nodes_buys_nothing():
    state = GameState(coins=10_000.0)
    view, _, _ = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)
    x, y = view.node_centre(0, 0)

    bought = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y + 40)),
        WIN_W, WIN_H)

    assert bought is False
    assert state.upgrade_ball_speed == 0


def test_clicking_a_node_you_cannot_afford_buys_nothing():
    state = GameState(coins=0.0)
    view, _, _ = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)

    bought = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                           pos=view.node_centre(0, 0)),
        WIN_W, WIN_H)

    assert bought is False
    assert state.upgrade_ball_speed == 0


def test_clicking_a_locked_node_buys_nothing():
    """Drugi węzeł gałęzi Piłka wymaga kupienia pierwszego."""
    state = GameState(coins=10_000.0)
    view, _, _ = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)

    bought = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                           pos=view.node_centre(0, 1)),
        WIN_W, WIN_H)

    assert bought is False
    assert state.upgrade_ball_size == 0


def test_click_targets_line_up_with_the_drawn_nodes():
    """Geometria kliknięcia i rysowania musi być tym samym wzorem. Gdy się
    rozjadą, obraz nadal wygląda poprawnie, a kliknięcia trafiają w pustkę."""
    state = GameState()
    view, surface, font = _view(state)
    view.draw(surface, font, WIN_W, WIN_H)

    checked = 0
    for col, branch in enumerate(_BRANCH_ORDER):
        for row in range(_rows(branch)):
            x, y = view.node_centre(col, row)
            if not view.node_area().collidepoint(x, y):
                continue                      # poza widocznym oknem przewijania
            assert surface.get_at((x, y))[:3] != _COL_BG, (branch, row)
            checked += 1

    assert checked >= 3


def test_every_node_can_be_reached_by_scrolling():
    """Przy domyślnym oknie trzy węzły leżały poza panelem — nie dało się
    kupić czegoś, czego nie widać."""
    state = GameState()
    view, surface, font = _view(state)

    for col, branch in enumerate(_BRANCH_ORDER):
        for row in range(_rows(branch)):
            reachable = False
            for scroll in range(0, 400, 10):
                view.scroll = scroll
                view.draw(surface, font, WIN_W, WIN_H)
                x, y = view.node_centre(col, row)
                if view.node_area().collidepoint(x, y):
                    reachable = True
                    break
            assert reachable, (branch, row)


def test_scrolling_moves_the_nodes_up():
    state = GameState()
    view, _, _ = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)
    before = view.node_centre(0, 0)[1]

    view.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1),
                      WIN_W, WIN_H)

    assert view.node_centre(0, 0)[1] < before


def test_scroll_stops_at_the_top_and_bottom():
    state = GameState()
    view, _, _ = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)

    for _ in range(50):
        view.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1),
                          WIN_W, WIN_H)
    assert view.scroll == 0

    for _ in range(100):
        view.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1),
                          WIN_W, WIN_H)
    assert view.scroll == view.max_scroll()


def test_drawing_with_a_hovered_node_does_not_crash():
    state = GameState(coins=10_000.0)
    view, surface, font = _view(state)
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)
    view.handle_event(
        pygame.event.Event(pygame.MOUSEMOTION, pos=view.node_centre(0, 0)),
        WIN_W, WIN_H)

    view.draw(surface, font, WIN_W, WIN_H)

    assert surface.get_at(view.node_centre(0, 0))[:3] != _COL_BG


# ----------------------------------------------------------------------
# Pasek szczegółów — treść wchłonięta ze sklepu
# ----------------------------------------------------------------------

def _hover(view: TreeView, col: int, row: int) -> None:
    """Ustawia rect widoku, a potem najeżdża na wskazany węzeł."""
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)
    view.handle_event(
        pygame.event.Event(pygame.MOUSEMOTION, pos=view.node_centre(col, row)),
        WIN_W, WIN_H)


def test_detail_bar_names_the_upgrade_and_its_level():
    view, _, _ = _view(GameState(upgrade_ball_speed=2))
    _hover(view, 0, 0)

    assert view.detail_lines()[0] == "Predkosc pilki  Lv.2/5"


def test_detail_bar_shows_the_upgrade_description():
    """Opis był wyłącznie w sklepie — bez niego węzeł nie mówi, co robi."""
    view, _, _ = _view(GameState())
    _hover(view, 0, 0)

    assert view.detail_lines()[1] == "+20% predkosci"


def test_detail_bar_names_the_upgrade_a_locked_node_requires():
    """Samo 'Zablokowane' nie mówi, co odblokować — sklep podawał nazwę."""
    view, _, _ = _view(GameState())
    _hover(view, 0, 1)

    assert view.detail_lines()[2] == "Wymaga: Predkosc pilki"


def test_detail_bar_shows_the_cost_of_an_available_upgrade():
    view, _, _ = _view(GameState(coins=10_000.0))
    _hover(view, 0, 0)

    assert view.detail_lines()[2].startswith("Koszt: ")


def test_detail_bar_reports_a_maxed_upgrade():
    view, _, _ = _view(GameState(upgrade_ball_speed=5))
    _hover(view, 0, 0)

    assert view.detail_lines()[2] == "MAX"


def test_detail_bar_is_empty_with_nothing_hovered():
    view, _, _ = _view(GameState())
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)

    assert view.detail_lines() == []


# ----------------------------------------------------------------------
# Przycisk Kup — jawna afordancja, której węzeł o promieniu 14 px nie daje
# ----------------------------------------------------------------------

def test_the_buy_button_purchases_the_hovered_upgrade():
    state = GameState(coins=10_000.0)
    view, _, _ = _view(state)
    _hover(view, 0, 0)

    bought = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                           pos=view.buy_btn_rect().center), WIN_W, WIN_H)

    assert bought is True
    assert state.upgrade_ball_speed == 1


def test_the_buy_button_does_nothing_without_the_coins():
    state = GameState(coins=0.0)
    view, _, _ = _view(state)
    _hover(view, 0, 0)

    bought = view.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                           pos=view.buy_btn_rect().center), WIN_W, WIN_H)

    assert bought is False
    assert state.upgrade_ball_speed == 0


def test_there_is_no_buy_button_on_a_locked_node():
    view, _, _ = _view(GameState(coins=10_000.0))
    _hover(view, 0, 1)

    assert view.buy_btn_rect() is None


def test_there_is_no_buy_button_on_a_maxed_node():
    view, _, _ = _view(GameState(upgrade_ball_speed=5, coins=10_000.0))
    _hover(view, 0, 0)

    assert view.buy_btn_rect() is None


def test_there_is_no_buy_button_with_nothing_hovered():
    view, _, _ = _view(GameState(coins=10_000.0))
    view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)),
                      WIN_W, WIN_H)

    assert view.buy_btn_rect() is None


def test_moving_onto_the_detail_bar_keeps_the_node_selected():
    """Kursor w drodze do przycisku opuszcza węzeł. Gdyby to czyściło wybór,
    pasek pustoszałby, zanim gracz dojedzie do Kup."""
    view, _, _ = _view(GameState(coins=10_000.0))
    _hover(view, 0, 0)
    selected = view.hovered

    view.handle_event(
        pygame.event.Event(pygame.MOUSEMOTION,
                           pos=view.detail_rect().center), WIN_W, WIN_H)

    assert view.hovered == selected


def _luminance(c: tuple[int, int, int]) -> float:
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def test_the_requirement_line_is_legible_on_the_detail_strip():
    """Sklep pisał stan zablokowany na tle wiersza (30,32,44). Pasek
    szczegółów jest prawie czarny, więc ten sam kolor zlewa się z tłem —
    a to akurat ten wiersz mówi graczowi, co odblokować."""
    view, _, _ = _view(GameState())
    _hover(view, 0, 1)

    assert view.detail_lines()[2].startswith("Wymaga:")
    assert abs(_luminance(view._status_color())
               - _luminance(_COL_DETAIL_BG)) >= 60
