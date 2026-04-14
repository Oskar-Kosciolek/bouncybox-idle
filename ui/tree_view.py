import pygame
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from upgrade_tree import Upgrade


_COL_BG     = (24, 24, 32)
_COL_TEXT   = (200, 200, 220)
_COL_DESC   = (120, 120, 140)
_COL_LOCKED = (55, 55, 70)
_COL_BORDER_BUY = (240, 210, 60)

_BRANCH_COLORS: dict[str, tuple[int, int, int]] = {
    "ball":    (220, 80,  80),
    "rings":   (80,  140, 220),
    "economy": (220, 200, 80),
}
_BRANCH_LABELS: dict[str, str] = {
    "ball":    "Pilka",
    "rings":   "Okregi",
    "economy": "Ekonomia",
}
_BRANCH_ORDER: list[str] = ["ball", "rings", "economy"]

_NODE_R   = 14    # promień węzła
_NODE_GAP = 78    # odstęp między węzłami (Y)
_HEADER_H = 36    # wysokość nagłówka gałęzi


class TreeView:
    """Wizualne drzewko ulepszeń — 3 kolumny (ball / rings / economy)."""

    def __init__(self, rect: pygame.Rect,
                 state: "GameState",
                 upgrades: list["Upgrade"]) -> None:
        self.rect = rect
        self.state = state
        self.upgrades = upgrades

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje drzewko ulepszeń."""
        pygame.draw.rect(surface, _COL_BG, self.rect)

        col_w = self.rect.width // 3

        for col_i, branch in enumerate(_BRANCH_ORDER):
            cx = self.rect.x + col_i * col_w + col_w // 2
            self._draw_branch(surface, font, branch, cx, col_w)

        pygame.draw.rect(surface, (40, 40, 55), self.rect, 1)

    def _draw_branch(self, surface: pygame.Surface, font: pygame.font.Font,
                     branch: str, cx: int, col_w: int) -> None:
        """Rysuje jedną kolumnę drzewka."""
        color = _BRANCH_COLORS[branch]
        label = _BRANCH_LABELS[branch]

        # Nagłówek gałęzi
        hdr_y = self.rect.y + 4
        hdr_surf = font.render(label, True, color)
        surface.blit(hdr_surf, hdr_surf.get_rect(centerx=cx, top=hdr_y))

        upgrades_in_branch = [u for u in self.upgrades if u.branch == branch]
        node_positions: list[tuple[int, int]] = []

        for j, upg in enumerate(upgrades_in_branch):
            ny = self.rect.y + _HEADER_H + j * _NODE_GAP + _NODE_R + 4

            # Linia łącząca z poprzednim węzłem (jeśli jest requires)
            if j > 0:
                prev_ny = self.rect.y + _HEADER_H + (j - 1) * _NODE_GAP + _NODE_R + 4
                line_col = (55, 55, 75)
                pygame.draw.line(surface, line_col, (cx, prev_ny + _NODE_R),
                                 (cx, ny - _NODE_R), 2)

            node_positions.append((cx, ny))
            self._draw_node(surface, font, upg, cx, ny, color)

    def _draw_node(self, surface: pygame.Surface, font: pygame.font.Font,
                   upg: "Upgrade", cx: int, cy: int,
                   branch_color: tuple[int, int, int]) -> None:
        """Rysuje pojedynczy węzeł z etykietą i paskiem postępu."""
        lvl = upg.current_level(self.state)
        maxed = upg.is_maxed(self.state)
        unlocked = upg.is_unlocked(self.state)
        can_buy = upg.can_afford(self.state) and unlocked and not maxed

        # Tło węzła
        if not unlocked:
            fill_col = _COL_LOCKED
        elif lvl > 0:
            # Wypełniony kolorem gałęzi (jasność zależy od poziomu)
            t = lvl / upg.max_level
            fill_col = tuple(int(c * (0.4 + 0.6 * t)) for c in branch_color)
        else:
            fill_col = (35, 35, 50)

        pygame.draw.circle(surface, fill_col, (cx, cy), _NODE_R)

        # Obramowanie: złote jeśli można kupić, branch_color jeśli maxed, szare inaczej
        if maxed:
            border_col = branch_color
            border_w = 2
        elif can_buy:
            border_col = _COL_BORDER_BUY
            border_w = 2
        else:
            border_col = (60, 60, 80)
            border_w = 1
        pygame.draw.circle(surface, border_col, (cx, cy), _NODE_R, border_w)

        # Poziom wewnątrz węzła
        if lvl > 0:
            lv_surf = font.render(str(lvl), True, (240, 240, 255))
            surface.blit(lv_surf, lv_surf.get_rect(center=(cx, cy)))

        # Pasek postępu (pod węzłem)
        bar_y = cy + _NODE_R + 4
        bar_w = _NODE_R * 2
        bar_h = 4
        bar_x = cx - _NODE_R
        pygame.draw.rect(surface, (40, 40, 55),
                         pygame.Rect(bar_x, bar_y, bar_w, bar_h))
        if upg.max_level > 0 and lvl > 0:
            fill_w = int(bar_w * lvl / upg.max_level)
            bar_col = branch_color if not maxed else (180, 220, 100)
            pygame.draw.rect(surface, bar_col,
                             pygame.Rect(bar_x, bar_y, fill_w, bar_h))

        # Nazwa ulepszenia (pod paskiem)
        name_y = bar_y + bar_h + 3
        # Skracamy nazwę jeśli za długa (max ~10 znaków)
        name = upg.name if len(upg.name) <= 11 else upg.name[:10] + "."
        name_col = _COL_DESC if not unlocked else _COL_TEXT
        name_surf = font.render(name, True, name_col)
        surface.blit(name_surf, name_surf.get_rect(centerx=cx, top=name_y))
