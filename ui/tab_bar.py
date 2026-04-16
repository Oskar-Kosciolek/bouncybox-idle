import pygame
from typing import Optional


class TabBar:
    """Pasek zakładek po prawej stronie okna."""

    TABS: list[tuple[str, str]] = [
        ("[G]", "Gra"),
        ("[S]", "Sklep"),
        ("[D]", "Drzewko"),
        ("[P]", "Prestige"),
        ("[A]", "Osiag."),
        ("[U]", "Ustaw."),
    ]

    TAB_HEIGHT: int = 44

    def __init__(self, width: int) -> None:
        self.width = width
        self.active: int = 0
        self.tab_height: int = self.TAB_HEIGHT

    def handle_event(self, event: pygame.event.Event,
                     current_game_w: int) -> Optional[int]:
        """Obsługuje kliknięcie zakładki. Zwraca indeks lub None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.TABS)):
                rect = self._tab_rect(i, current_game_w)
                if rect.collidepoint(event.pos):
                    self.active = i
                    return i
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             current_game_w: int, current_game_h: int) -> None:
        """Rysuje wszystkie zakładki."""
        for i, (icon, name) in enumerate(self.TABS):
            rect = self._tab_rect(i, current_game_w)
            # Tło zakładki
            bg = (40, 50, 70) if i == self.active else (24, 24, 32)
            pygame.draw.rect(surface, bg, rect)
            # Obramowanie
            border = (80, 110, 160) if i == self.active else (40, 40, 55)
            pygame.draw.rect(surface, border, rect, 1)
            # Pasek aktywności po lewej stronie aktywnej zakładki
            if i == self.active:
                pygame.draw.rect(surface, (100, 160, 255),
                                 pygame.Rect(current_game_w, rect.y + 4, 3, rect.height - 8))
            # Tekst: emoji + nazwa
            label = f"{icon} {name}"
            color = (230, 230, 250) if i == self.active else (130, 130, 150)
            txt = font.render(label, True, color)
            surface.blit(txt, txt.get_rect(center=rect.center))

    def _tab_rect(self, index: int, x: int) -> pygame.Rect:
        """Zwraca prostokąt zakładki o danym indeksie."""
        return pygame.Rect(x, index * self.tab_height, self.width, self.tab_height)


TAB_TOTAL_HEIGHT: int = len(TabBar.TABS) * TabBar.TAB_HEIGHT
