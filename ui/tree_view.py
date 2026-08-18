import pygame
import math
from typing import TYPE_CHECKING

from constants import PANEL_W
from ui.tab_bar import TAB_TOTAL_HEIGHT
from formatting import short_number

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
# 60, bo od środka węzła w dół zajęte jest 43 px (koło, pasek, nazwa),
# a kolejne koło zaczyna się 14 px przed swoim środkiem — poniżej 58 px
# nazwa wchodziłaby pod następny węzeł.
_NODE_GAP = 60    # odstęp między węzłami (Y)
_HEADER_H = 36    # wysokość nagłówka gałęzi
_DETAIL_H = 46    # pasek szczegółów u dołu — nie przewija się razem z węzłami
_SCROLL_STEP = 26


class TreeView:
    """Wizualne drzewko ulepszeń — 3 kolumny (ball / rings / economy)."""

    def __init__(self,
                 state: "GameState",
                 upgrades: list["Upgrade"]) -> None:
        self.rect: pygame.Rect | None = None
        self.state = state
        self.upgrades = upgrades
        self.scroll: int = 0
        # Węzeł pod kursorem — (kolumna, rząd) albo None
        self.hovered: tuple[int, int] | None = None


    # ------------------------------------------------------------------
    # Geometria — wspólna dla rysowania i klikania
    # ------------------------------------------------------------------

    def _set_rect(self, current_game_w: int, current_game_h: int) -> None:
        self.rect = pygame.Rect(current_game_w, TAB_TOTAL_HEIGHT,
                                PANEL_W, current_game_h - TAB_TOTAL_HEIGHT)

    def node_area(self) -> pygame.Rect:
        """Przewijalny obszar węzłów — panel bez paska szczegółów u dołu."""
        return pygame.Rect(self.rect.x, self.rect.y,
                           self.rect.width, self.rect.height - _DETAIL_H)

    def branch_upgrades(self, col: int) -> list["Upgrade"]:
        branch = _BRANCH_ORDER[col]
        return [u for u in self.upgrades if u.branch == branch]

    def node_centre(self, col: int, row: int) -> tuple[int, int]:
        """Środek węzła. Jedyne miejsce, które zna ten wzór.

        Gdyby rysowanie i klikanie liczyły go osobno, rozjechałyby się przy
        pierwszej zmianie odstępów — a obraz nadal wyglądałby poprawnie,
        więc nikt by tego nie zauważył poza graczem trafiającym w pustkę.
        """
        col_w = self.rect.width // 3
        x = self.rect.x + col * col_w + col_w // 2
        y = (self.rect.y + _HEADER_H + row * _NODE_GAP + _NODE_R + 4
             - self.scroll)
        return x, y

    def _content_height(self) -> int:
        rows = max(len(self.branch_upgrades(c)) for c in range(3))
        return _HEADER_H + rows * _NODE_GAP + _NODE_R

    def max_scroll(self) -> int:
        return max(0, self._content_height() - self.node_area().height)

    def _node_at(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """Który węzeł jest pod podanym punktem, jeśli którykolwiek."""
        if not self.node_area().collidepoint(pos):
            return None
        for col in range(3):
            for row in range(len(self.branch_upgrades(col))):
                cx, cy = self.node_centre(col, row)
                if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= _NODE_R ** 2:
                    return col, row
        return None

    # ------------------------------------------------------------------
    # Zdarzenia
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event,
                     current_game_w: int, current_game_h: int) -> bool:
        """Obsługuje kliknięcia i przewijanie. Zwraca True, gdy coś kupiono."""
        self._set_rect(current_game_w, current_game_h)

        if event.type == pygame.MOUSEWHEEL:
            # Bez sprawdzania pozycji myszy: main.py kieruje tu zdarzenia
            # tylko przy aktywnej zakładce, więc panel jest jedynym widokiem.
            # Odpytywanie pygame.mouse wymagałoby też zainicjowanego wideo.
            self.scroll = max(0, min(self.scroll - event.y * _SCROLL_STEP,
                                     self.max_scroll()))
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self._node_at(event.pos)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            found = self._node_at(event.pos)
            if found is None:
                return False
            col, row = found
            return self.branch_upgrades(col)[row].purchase(self.state)

        return False

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             current_game_w: int, current_game_h: int) -> None:
        """Rysuje drzewko ulepszeń."""
        self._set_rect(current_game_w, current_game_h)
        self.scroll = max(0, min(self.scroll, self.max_scroll()))
        pygame.draw.rect(surface, _COL_BG, self.rect)

        # Węzły przewijają się, więc rysujemy je przycięte do swojego obszaru
        old_clip = surface.get_clip()
        surface.set_clip(self.node_area())
        for col in range(3):
            self._draw_branch(surface, font, col)
        surface.set_clip(old_clip)

        self._draw_detail(surface, font)
        pygame.draw.rect(surface, (40, 40, 55), self.rect, 1)

    def _draw_branch(self, surface: pygame.Surface, font: pygame.font.Font,
                     col: int) -> None:
        """Rysuje jedną kolumnę drzewka."""
        branch = _BRANCH_ORDER[col]
        color = _BRANCH_COLORS[branch]

        # Nagłówek gałęzi — przewija się razem z węzłami
        cx, _ = self.node_centre(col, 0)
        hdr_surf = font.render(_BRANCH_LABELS[branch], True, color)
        surface.blit(hdr_surf, hdr_surf.get_rect(
            centerx=cx, top=self.rect.y + 4 - self.scroll))

        for row, upg in enumerate(self.branch_upgrades(col)):
            _, ny = self.node_centre(col, row)

            # Linia łącząca z poprzednim węzłem
            if row > 0:
                _, prev_ny = self.node_centre(col, row - 1)
                pygame.draw.line(surface, (55, 55, 75), (cx, prev_ny + _NODE_R),
                                 (cx, ny - _NODE_R), 2)

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
            # Wypełniony kolorem gałęzi (jasność zależy od poziomu).
            # Bez sufitu nie ma ułamka postępu — węzeł świeci pełnią.
            t = 1.0 if upg.max_level is None else lvl / upg.max_level
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
        if lvl > 0 and (upg.max_level is None or upg.max_level > 0):
            ratio = 1.0 if upg.max_level is None else lvl / upg.max_level
            fill_w = int(bar_w * ratio)
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

    def _draw_detail(self, surface: pygame.Surface,
                     font: pygame.font.Font) -> None:
        """Pasek u dołu: szczegóły węzła pod kursorem.

        Węzeł ma 28 px średnicy w kolumnie szerokiej na 60 — nie zmieści się
        w nim cena. Bez niej klikanie byłoby kupowaniem w ciemno.
        """
        strip = pygame.Rect(self.rect.x, self.rect.bottom - _DETAIL_H,
                            self.rect.width, _DETAIL_H)
        pygame.draw.rect(surface, (20, 20, 28), strip)
        pygame.draw.line(surface, (40, 40, 55),
                         strip.topleft, strip.topright)

        if self.hovered is None:
            hint = font.render("Najedz na wezel", True, (90, 90, 110))
            surface.blit(hint, hint.get_rect(center=strip.center))
            return

        col, row = self.hovered
        upg = self.branch_upgrades(col)[row]
        lvl = upg.current_level(self.state)

        level_str = f"Lv.{lvl}" if upg.max_level is None \
            else f"Lv.{lvl}/{upg.max_level}"
        surface.blit(font.render(f"{upg.name}  {level_str}", True, _COL_TEXT),
                     (strip.x + 6, strip.y + 4))

        if upg.is_maxed(self.state):
            status, color = "MAX", (120, 200, 120)
        elif not upg.is_unlocked(self.state):
            status, color = "Zablokowane", _COL_LOCKED
        else:
            cost = upg.cost_at_level(lvl)
            affordable = upg.can_afford(self.state)
            status = f"Koszt: {short_number(cost)}"
            color = _COL_BORDER_BUY if affordable else _COL_DESC
        surface.blit(font.render(status, True, color),
                     (strip.x + 6, strip.y + 20))
