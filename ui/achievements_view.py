import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from achievements import Achievement

# Kolory
_COL_BG          = (24, 24, 32)
_COL_ITEM_BG     = (30, 32, 44)
_COL_ITEM_LOCKED = (26, 26, 36)
_COL_BORDER      = (50, 55, 75)
_COL_TEXT        = (210, 210, 230)
_COL_TEXT_LOCKED = (80, 80, 100)
_COL_DESC        = (140, 140, 160)
_COL_DESC_LOCKED = (60, 60, 80)
_COL_DONE        = (60, 200, 100)
_COL_CRYSTAL     = (150, 220, 255)
_COL_HDR         = (180, 180, 200)

_ITEM_H = 52    # wysokość wiersza osiągnięcia
_HDR_H  = 28    # wysokość nagłówka


class AchievementsView:
    """Widok listy osiągnięć — odblokowane i zablokowane."""

    def __init__(self, rect: pygame.Rect,
                 state: "GameState",
                 achievements: list["Achievement"]) -> None:
        self.rect = rect
        self.state = state
        self.achievements = achievements
        self.scroll: int = 0

    # ------------------------------------------------------------------
    # Obsługa zdarzeń
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Obsługuje scrollowanie listy osiągnięć."""
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll(event.y * -20)

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje cały widok osiągnięć."""
        pygame.draw.rect(surface, _COL_BG, self.rect)

        # Nagłówek z licznikiem
        unlocked_count = len(self.state.achievements_unlocked)
        total = len(self.achievements)
        hdr = f"Osiagniecia {unlocked_count}/{total}"
        hdr_surf = font.render(hdr, True, _COL_HDR)
        surface.blit(hdr_surf, hdr_surf.get_rect(
            centerx=self.rect.centerx, top=self.rect.y + 6))

        # Obszar listy (poniżej nagłówka)
        list_y = self.rect.y + _HDR_H
        list_rect = pygame.Rect(self.rect.x, list_y, self.rect.width, self.rect.bottom - list_y)

        old_clip = surface.get_clip()
        surface.set_clip(list_rect)

        for i, ach in enumerate(self.achievements):
            self._draw_achievement(surface, font, i, ach, list_y)

        surface.set_clip(old_clip)
        pygame.draw.rect(surface, (40, 40, 55), self.rect, 1)

    def _draw_achievement(self, surface: pygame.Surface,
                          font: pygame.font.Font,
                          index: int, ach: "Achievement",
                          list_top: int) -> None:
        """Rysuje jeden wiersz osiągnięcia."""
        item_rect = self._item_rect(index, list_top)
        unlocked = ach.id in self.state.achievements_unlocked

        # Tło
        bg = _COL_ITEM_BG if unlocked else _COL_ITEM_LOCKED
        pygame.draw.rect(surface, bg, item_rect)
        pygame.draw.rect(surface, _COL_BORDER, item_rect, 1)

        ix = item_rect.x + 6
        iy = item_rect.y + 6

        # Ikona stanu
        if unlocked:
            icon_col = _COL_DONE
            icon = "[V]"
        else:
            icon_col = _COL_TEXT_LOCKED
            icon = "[ ]"
        icon_surf = font.render(icon, True, icon_col)
        surface.blit(icon_surf, (ix, iy))

        # Nazwa osiągnięcia
        name_col = _COL_TEXT if unlocked else _COL_TEXT_LOCKED
        name_surf = font.render(ach.name, True, name_col)
        surface.blit(name_surf, (ix + 28, iy))

        # Nagroda w kryształach (jeśli jest)
        if ach.reward_crystals > 0:
            crystal_str = f"+{ach.reward_crystals} krysz."
            cr_surf = font.render(crystal_str, True, _COL_CRYSTAL)
            surface.blit(cr_surf, (item_rect.right - cr_surf.get_width() - 6, iy))

        # Opis
        desc_col = _COL_DESC if unlocked else _COL_DESC_LOCKED
        desc_surf = font.render(ach.description, True, desc_col)
        surface.blit(desc_surf, (ix + 28, iy + 16))

    # ------------------------------------------------------------------
    # Pomocnicze prostokąty
    # ------------------------------------------------------------------

    def _item_rect(self, index: int, list_top: int) -> pygame.Rect:
        """Prostokąt wiersza osiągnięcia z uwzględnieniem scrolla."""
        y = list_top + index * _ITEM_H - self.scroll
        return pygame.Rect(self.rect.x, y, self.rect.width, _ITEM_H)

    def _scroll(self, delta: int) -> None:
        """Przesuwa listę osiągnięć."""
        list_h = self.rect.height - _HDR_H
        max_scroll = max(0, len(self.achievements) * _ITEM_H - list_h)
        self.scroll = max(0, min(self.scroll + delta, max_scroll))
