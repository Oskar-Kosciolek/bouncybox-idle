import pygame

from game_state import GameState
from ui.shop_view import ShopView
from ui.tree_view import TreeView
from upgrade_tree import UPGRADES

pygame.font.init()   # czcionki działają bez okna — set_mode nie jest potrzebne


def _draw(view_cls, state) -> bytes:
    surface = pygame.Surface((700, 520))
    font = pygame.font.SysFont("segoeui", 13)
    view_cls(state, UPGRADES).draw(surface, font, 520, 520)
    return pygame.image.tobytes(surface, "RGB")


def test_shop_draws_an_unbounded_upgrade():
    """Ulepszenie bez sufitu ma max_level = None. Sklep sklejał z tego napis
    'Lv.7/None', a drzewko dzieliło przez None i wywalało całą zakładkę —
    obie awarie są niewidoczne dla testów logiki."""
    pixels = _draw(ShopView, GameState(upgrade_ball_damage=7))

    assert pixels != pygame.image.tobytes(pygame.Surface((700, 520)), "RGB")


def test_tree_draws_an_unbounded_upgrade():
    pixels = _draw(TreeView, GameState(upgrade_ball_damage=7))

    assert pixels != pygame.image.tobytes(pygame.Surface((700, 520)), "RGB")


def test_tree_draws_a_fresh_game():
    """Poziom 0 przy braku sufitu też musi przejść — inny gałąź kodu."""
    pixels = _draw(TreeView, GameState())

    assert pixels != pygame.image.tobytes(pygame.Surface((700, 520)), "RGB")
