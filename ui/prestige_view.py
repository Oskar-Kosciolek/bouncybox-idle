import pygame
from typing import TYPE_CHECKING, Callable

from constants import PANEL_W
from ui.tab_bar import TAB_TOTAL_HEIGHT

if TYPE_CHECKING:
    from game_state import GameState
    from upgrade_tree import PrestigeUpgrade

# Kolory
_COL_BG          = (24, 24, 32)
_COL_ITEM_BG     = (30, 32, 44)
_COL_ITEM_BORDER = (50, 55, 75)
_COL_TEXT        = (210, 210, 230)
_COL_DESC        = (140, 140, 160)
_COL_CRYSTAL     = (150, 220, 255)
_COL_BUY_ON      = (50, 130, 200)
_COL_BUY_OFF     = (55, 55, 70)
_COL_MAX         = (80, 80, 100)
_COL_WARN        = (220, 80, 80)
_COL_PRESTIGE_OK = (60, 180, 80)
_COL_PRESTIGE_NO = (70, 70, 90)

_ITEM_H  = 74    # wysokość wiersza ulepszenia prestige
_BTN_H   = 24    # wysokość przycisku Kup
_HDR_H   = 38    # wysokość nagłówka
_PBTN_H  = 38    # wysokość przycisku PRESTIGE


class PrestigeView:
    """Widok ekranu prestige — przycisk resetu i ulepszenia permanentne."""

    def __init__(self,
                 state: "GameState",
                 prestige_upgrades: list["PrestigeUpgrade"]) -> None:
        self.rect: pygame.Rect | None = None
        self.state = state
        self.prestige_upgrades = prestige_upgrades
        self.scroll: int = 0

    # ------------------------------------------------------------------
    # Obsługa zdarzeń
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event,
                     on_prestige_callback: Callable[[], None],
                     current_game_w: int, current_game_h: int) -> None:
        """Obsługuje kliknięcia przycisku PRESTIGE i zakupów ulepszeń."""
        self.rect = pygame.Rect(current_game_w, TAB_TOTAL_HEIGHT,
                                PANEL_W, current_game_h - TAB_TOTAL_HEIGHT)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos, on_prestige_callback)
        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll(event.y * -20)

    def _handle_click(self, pos: tuple[int, int],
                      on_prestige_callback: Callable[[], None]) -> None:
        """Obsługuje kliknięcie w obszarze widoku."""
        # Przycisk PRESTIGE
        pbtn = self._prestige_btn_rect()
        if pbtn.collidepoint(pos) and self.state.wave >= 10:
            on_prestige_callback()
            self.scroll = 0
            return

        # Przyciski zakupu ulepszeń prestige
        for i, upg in enumerate(self.prestige_upgrades):
            btn = self._buy_btn_rect(i)
            if btn and btn.collidepoint(pos):
                upg.purchase(self.state)
                return

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             current_game_w: int, current_game_h: int) -> None:
        """Rysuje cały widok prestige."""
        self.rect = pygame.Rect(current_game_w, TAB_TOTAL_HEIGHT,
                                PANEL_W, current_game_h - TAB_TOTAL_HEIGHT)
        pygame.draw.rect(surface, _COL_BG, self.rect)

        y = self.rect.y + 6

        # Nagłówek — liczba prestigeów i kryształów
        y = self._draw_header(surface, font, y)

        # Przycisk PRESTIGE
        y = self._draw_prestige_button(surface, font, y)

        # Ostrzeżenie o resecie
        y = self._draw_warning(surface, font, y)

        # Separator
        pygame.draw.line(surface, (50, 55, 75),
                         (self.rect.x + 4, y),
                         (self.rect.right - 4, y), 1)
        y += 6

        # Lista ulepszeń prestige (z kliping + scrollem)
        list_rect = pygame.Rect(self.rect.x, y, self.rect.width, self.rect.bottom - y)
        old_clip = surface.get_clip()
        surface.set_clip(list_rect)

        for i, upg in enumerate(self.prestige_upgrades):
            self._draw_upgrade_item(surface, font, i, upg, y)

        surface.set_clip(old_clip)
        pygame.draw.rect(surface, (40, 40, 55), self.rect, 1)

    def _draw_header(self, surface: pygame.Surface,
                     font: pygame.font.Font, y: int) -> int:
        """Rysuje nagłówek z licznikami. Zwraca nowe y."""
        hdr = f"Prestige #{self.state.prestige_count}  |  {self.state.prestige_crystals} krysztalow"
        surf = font.render(hdr, True, _COL_CRYSTAL)
        surface.blit(surf, surf.get_rect(centerx=self.rect.centerx, top=y))
        return y + surf.get_height() + 6

    def _draw_prestige_button(self, surface: pygame.Surface,
                              font: pygame.font.Font, y: int) -> int:
        """Rysuje przycisk PRESTIGE i informację o kryształach. Zwraca nowe y."""
        btn = self._prestige_btn_rect(y_override=y)
        available = self.state.wave >= 10

        # Kolor przycisku
        col = _COL_PRESTIGE_OK if available else _COL_PRESTIGE_NO
        pygame.draw.rect(surface, col, btn, border_radius=5)
        pygame.draw.rect(surface, (80, 80, 100), btn, 1, border_radius=5)

        if available:
            label = f"PRESTIGE (fala {self.state.wave}/10)"
        else:
            label = "Wymagana fala 10"
        txt = font.render(label, True, (230, 230, 240))
        surface.blit(txt, txt.get_rect(center=btn.center))

        y = btn.bottom + 4

        # Ile kryształów dostaniemy
        crystals_gain = 1 + self.state.prestige_count // 2
        sub = font.render(f"Otrzymasz: {crystals_gain} krysztalow", True, _COL_CRYSTAL)
        surface.blit(sub, sub.get_rect(centerx=self.rect.centerx, top=y))
        return y + sub.get_height() + 4

    def _draw_warning(self, surface: pygame.Surface,
                      font: pygame.font.Font, y: int) -> int:
        """Rysuje czerwone ostrzeżenie. Zwraca nowe y."""
        warn = font.render("! Prestige resetuje monety i ulepszenia!", True, _COL_WARN)
        surface.blit(warn, warn.get_rect(centerx=self.rect.centerx, top=y))
        return y + warn.get_height() + 6

    def _draw_upgrade_item(self, surface: pygame.Surface,
                           font: pygame.font.Font,
                           index: int, upg: "PrestigeUpgrade",
                           list_top: int) -> None:
        """Rysuje jeden wiersz ulepszenia prestige."""
        item_rect = self._item_rect(index, list_top)
        pygame.draw.rect(surface, _COL_ITEM_BG, item_rect)
        pygame.draw.rect(surface, _COL_ITEM_BORDER, item_rect, 1)

        lvl = upg.current_level(self.state)
        maxed = upg.is_maxed(self.state)
        affordable = upg.can_afford(self.state)

        ix = item_rect.x + 6
        iy = item_rect.y + 5

        # Wiersz 1: nazwa + poziom
        name_str = f"{upg.name}  Lv.{lvl}/{upg.max_level}"
        name_surf = font.render(name_str, True, _COL_TEXT)
        surface.blit(name_surf, (ix, iy))

        # Wiersz 2: opis
        desc_surf = font.render(upg.description, True, _COL_DESC)
        surface.blit(desc_surf, (ix, iy + 16))

        # Wiersz 3: koszt + przycisk
        btn_y = item_rect.y + item_rect.height - _BTN_H - 5
        btn_w = 38
        btn_x = item_rect.right - btn_w - 6

        if maxed:
            tag = font.render("MAX", True, _COL_MAX)
            surface.blit(tag, (ix, btn_y + 4))
        else:
            cost_col = _COL_CRYSTAL if affordable else _COL_DESC
            cost_surf = font.render(f"{upg.cost_crystals} krysztalow", True, cost_col)
            surface.blit(cost_surf, (ix, btn_y + 4))

            buy_rect = pygame.Rect(btn_x, btn_y, btn_w, _BTN_H)
            buy_col = _COL_BUY_ON if affordable else _COL_BUY_OFF
            pygame.draw.rect(surface, buy_col, buy_rect, border_radius=4)
            buy_txt = font.render("Kup", True, (230, 230, 240))
            surface.blit(buy_txt, buy_txt.get_rect(center=buy_rect.center))

    # ------------------------------------------------------------------
    # Pomocnicze prostokąty
    # ------------------------------------------------------------------

    def _prestige_btn_rect(self, y_override: int | None = None) -> pygame.Rect:
        """Prostokąt przycisku PRESTIGE."""
        y = y_override if y_override is not None else (self.rect.y + _HDR_H)
        return pygame.Rect(self.rect.x + 6, y, self.rect.width - 12, _PBTN_H)

    def _item_rect(self, index: int, list_top: int) -> pygame.Rect:
        """Prostokąt wiersza ulepszenia z uwzględnieniem scrolla."""
        y = list_top + index * _ITEM_H - self.scroll
        return pygame.Rect(self.rect.x, y, self.rect.width, _ITEM_H)

    def _buy_btn_rect(self, index: int) -> pygame.Rect | None:
        """Prostokąt przycisku Kup. Zwraca None jeśli maxed."""
        upg = self.prestige_upgrades[index]
        if upg.is_maxed(self.state):
            return None
        # Szacuj list_top jako rect.y + nagłówek + prestige_btn + ostrzeżenie + separator
        list_top = self.rect.y + _HDR_H + _PBTN_H + 38 + 16
        item_rect = self._item_rect(index, list_top)
        btn_w = 38
        btn_h = _BTN_H
        btn_y = item_rect.y + item_rect.height - btn_h - 5
        btn_x = item_rect.right - btn_w - 6
        return pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    def _scroll(self, delta: int) -> None:
        """Przesuwa listę ulepszeń prestige."""
        max_scroll = max(0, len(self.prestige_upgrades) * _ITEM_H - 80)
        self.scroll = max(0, min(self.scroll + delta, max_scroll))
