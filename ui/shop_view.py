import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from upgrade_tree import Upgrade


# Kolory interfejsu sklepu
_COL_BG          = (24, 24, 32)
_COL_ITEM_BG     = (30, 32, 44)
_COL_ITEM_BORDER = (50, 55, 75)
_COL_TEXT        = (210, 210, 230)
_COL_DESC        = (140, 140, 160)
_COL_COST        = (220, 200, 80)
_COL_BUY_ON      = (50, 160, 80)
_COL_BUY_OFF     = (55, 55, 70)
_COL_MAX         = (80, 80, 100)
_COL_LOCKED      = (70, 70, 90)

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

_ITEM_H    = 80    # wysokość jednego wiersza ulepszenia
_BTN_H     = 26    # wysokość przycisku Kup
_BRANCH_H  = 28    # wysokość paska gałęzi


class ShopView:
    """Widok sklepu z listą ulepszeń i możliwością zakupu."""

    def __init__(self, rect: pygame.Rect,
                 state: "GameState",
                 upgrades: list["Upgrade"]) -> None:
        self.rect = rect
        self.state = state
        self.upgrades = upgrades
        self.active_branch: str = "ball"
        self.scroll: int = 0      # offset scrolla w pikselach

    # ------------------------------------------------------------------
    # Obsługa zdarzeń
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Obsługuje kliknięcia w przyciski gałęzi i zakupy ulepszeń."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll(event.y * -20)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        """Obsługuje kliknięcie LPM w dowolnym miejscu widoku."""
        # Przyciski gałęzi
        for i, branch in enumerate(_BRANCH_ORDER):
            btn = self._branch_btn_rect(i)
            if btn.collidepoint(pos):
                self.active_branch = branch
                self.scroll = 0
                return

        # Przyciski "Kup"
        filtered = self._filtered_upgrades()
        for j, upg in enumerate(filtered):
            buy_rect = self._buy_btn_rect(j)
            if buy_rect and buy_rect.collidepoint(pos):
                upg.purchase(self.state)
                return

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje cały widok sklepu."""
        pygame.draw.rect(surface, _COL_BG, self.rect)

        # Nagłówek
        self._draw_header(surface, font)

        # Przyciski gałęzi
        for i, branch in enumerate(_BRANCH_ORDER):
            self._draw_branch_btn(surface, font, i, branch)

        # Obszar listy ulepszeń
        list_y = self.rect.y + _BRANCH_H
        list_h = self.rect.height - _BRANCH_H
        list_rect = pygame.Rect(self.rect.x, list_y, self.rect.width, list_h)

        # Przycinamy rysowanie do obszaru listy
        old_clip = surface.get_clip()
        surface.set_clip(list_rect)

        filtered = self._filtered_upgrades()
        for j, upg in enumerate(filtered):
            self._draw_upgrade_item(surface, font, j, upg)

        surface.set_clip(old_clip)

        # Obramowanie zewnętrzne
        pygame.draw.rect(surface, (40, 40, 55), self.rect, 1)

    def _draw_header(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje pasek z przyciskami gałęzi."""
        hdr = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, _BRANCH_H)
        pygame.draw.rect(surface, (20, 20, 30), hdr)

    def _draw_branch_btn(self, surface: pygame.Surface, font: pygame.font.Font,
                         i: int, branch: str) -> None:
        """Rysuje jeden przycisk gałęzi."""
        btn = self._branch_btn_rect(i)
        active = branch == self.active_branch
        bg = _BRANCH_COLORS[branch] if active else (35, 35, 50)
        pygame.draw.rect(surface, bg, btn)
        pygame.draw.rect(surface, (50, 50, 70), btn, 1)
        label = _BRANCH_LABELS[branch]
        col = (255, 255, 255) if active else (120, 120, 140)
        txt = font.render(label, True, col)
        surface.blit(txt, txt.get_rect(center=btn.center))

    def _draw_upgrade_item(self, surface: pygame.Surface, font: pygame.font.Font,
                           index: int, upg: "Upgrade") -> None:
        """Rysuje jeden wiersz ulepszenia."""
        item_rect = self._item_rect(index)
        pygame.draw.rect(surface, _COL_ITEM_BG, item_rect)
        pygame.draw.rect(surface, _COL_ITEM_BORDER, item_rect, 1)

        lvl = upg.current_level(self.state)
        maxed = upg.is_maxed(self.state)
        unlocked = upg.is_unlocked(self.state)
        affordable = upg.can_afford(self.state)

        ix = item_rect.x + 6
        iy = item_rect.y + 5

        # Wiersz 1: nazwa + poziom
        name_col = _COL_DESC if not unlocked else _COL_TEXT
        name_str = f"{upg.name}  Lv.{lvl}/{upg.max_level}"
        name_surf = font.render(name_str, True, name_col)
        surface.blit(name_surf, (ix, iy))

        # Wiersz 2: opis
        desc_surf = font.render(upg.description, True, _COL_DESC)
        surface.blit(desc_surf, (ix, iy + 16))

        # Wiersz 3: koszt / stan + przycisk Kup
        btn_y = item_rect.y + item_rect.height - _BTN_H - 6
        btn_w = 38
        btn_x = item_rect.right - btn_w - 6

        if maxed:
            tag_surf = font.render("MAX", True, _COL_MAX)
            surface.blit(tag_surf, (ix, btn_y + 6))
        elif not unlocked:
            # Znajdź nazwę wymaganego ulepszenia
            req_name = self._find_upgrade_name(upg.requires)
            lock_surf = font.render(f"Wymaga: {req_name}", True, _COL_LOCKED)
            surface.blit(lock_surf, (ix, btn_y + 6))
        else:
            cost = upg.cost_at_level(lvl)
            cost_surf = font.render(f"{cost:.0f}", True,
                                    _COL_COST if affordable else _COL_DESC)
            surface.blit(cost_surf, (ix, btn_y + 6))

            # Przycisk Kup
            buy_rect = pygame.Rect(btn_x, btn_y, btn_w, _BTN_H)
            buy_col = _COL_BUY_ON if affordable else _COL_BUY_OFF
            pygame.draw.rect(surface, buy_col, buy_rect, border_radius=4)
            buy_txt = font.render("Kup", True, (230, 230, 240))
            surface.blit(buy_txt, buy_txt.get_rect(center=buy_rect.center))

    # ------------------------------------------------------------------
    # Pomocnicze metody obliczeniowe
    # ------------------------------------------------------------------

    def _branch_btn_rect(self, i: int) -> pygame.Rect:
        """Prostokąt przycisku gałęzi (3 równe kolumny w poziomie)."""
        w = self.rect.width // 3
        return pygame.Rect(self.rect.x + i * w, self.rect.y, w, _BRANCH_H)

    def _item_rect(self, index: int) -> pygame.Rect:
        """Prostokąt wiersza ulepszenia (z uwzględnieniem scrolla)."""
        list_y = self.rect.y + _BRANCH_H
        y = list_y + index * _ITEM_H - self.scroll
        return pygame.Rect(self.rect.x, y, self.rect.width, _ITEM_H)

    def _buy_btn_rect(self, index: int) -> pygame.Rect | None:
        """Prostokąt przycisku Kup. Zwraca None jeśli nie dotyczy."""
        upg = self._filtered_upgrades()[index]
        if upg.is_maxed(self.state) or not upg.is_unlocked(self.state):
            return None
        item_rect = self._item_rect(index)
        btn_w = 38
        btn_h = _BTN_H
        btn_y = item_rect.y + item_rect.height - btn_h - 6
        btn_x = item_rect.right - btn_w - 6
        return pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    def _filtered_upgrades(self) -> list["Upgrade"]:
        """Zwraca ulepszenia aktywnej gałęzi."""
        return [u for u in self.upgrades if u.branch == self.active_branch]

    def _find_upgrade_name(self, upg_id: str | None) -> str:
        """Zwraca nazwę ulepszenia po jego id."""
        if upg_id is None:
            return ""
        for u in self.upgrades:
            if u.id == upg_id:
                return u.name
        return upg_id

    def _scroll(self, delta: int) -> None:
        """Przesuwa listę. Ogranicza scroll do zakresu treści."""
        filtered = self._filtered_upgrades()
        max_scroll = max(0, len(filtered) * _ITEM_H - (self.rect.height - _BRANCH_H))
        self.scroll = max(0, min(self.scroll + delta, max_scroll))
