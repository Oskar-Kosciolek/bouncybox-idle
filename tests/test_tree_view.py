import pygame

from game_state import GameState
from ui.tree_view import _BRANCH_ORDER, _COL_BG, TreeView
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


def test_shop_reports_whether_a_purchase_happened():
    """main.py wykrywał zakup porównując str(state.__dict__) przed i po —
    budowa tekstu całego stanu przy każdym ruchu myszy, i to samo trzeba by
    zdublować dla drzewka."""
    from ui.shop_view import ShopView

    state = GameState(coins=10_000.0)
    shop = ShopView(state, UPGRADES)
    surface = pygame.Surface((700, WIN_H))
    shop.draw(surface, pygame.font.SysFont("segoeui", 13), WIN_W, WIN_H)

    buy_rect = shop._buy_btn_rect(0)
    bought = shop.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                           pos=buy_rect.center), WIN_W, WIN_H)
    missed = shop.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)),
        WIN_W, WIN_H)

    assert bought is True
    assert missed is False
