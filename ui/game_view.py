import pygame
from typing import TYPE_CHECKING

from constants import PANEL_W
from formatting import short_number
from ui.tab_bar import TAB_TOTAL_HEIGHT

if TYPE_CHECKING:
    from game_state import GameState


_COL_TEXT      = (220, 220, 240)
_COL_COIN      = (220, 200, 80)
_COL_WAVE      = (100, 180, 255)
_COL_BAR_BG    = (40, 40, 55)
_COL_BAR_FILL  = (80, 180, 100)
_COL_BAR_FULL  = (100, 220, 120)
_COL_PANEL_BG  = (24, 24, 32)
_COL_HEADER    = (120, 120, 160)
_COL_KEY       = (220, 200, 80)
_COL_HINT      = (140, 140, 160)


class GameView:
    """Zakładka Gra: nakładka HUD nad planszą i ściąga w panelu obok."""

    # Skróty klawiszowe. Trzymane jako dane, nie wklejone w rysowanie, bo
    # test pilnuje, że pokrywają się z tabelą w README — a README już raz
    # przeżył usunięcie całej zakładki, nic o tym nie wiedząc.
    CONTROLS: list[tuple[str, str]] = [
        ("ESC", "zapis i wyjscie"),
        ("R",   "nowa runda"),
        ("F5",  "reczny zapis"),
        ("F6",  "twardy reset"),
    ]

    # Panel ma 180 px, więc każda linia jest łamana ręcznie — automatyczne
    # zawijanie dla czterech zdań byłoby droższe niż same zdania.
    HINTS: list[str] = [
        "Klik w wezel drzewka",
        "kupuje jeden poziom.",
        "",
        "Najedz kursorem, zeby",
        "zobaczyc opis i cene.",
        "",
        "Reset jest tez na dole",
        "zakladki Ustawienia.",
    ]

    def __init__(self) -> None:
        pass

    def draw_controls(self, surface: pygame.Surface,
                      font: pygame.font.Font,
                      current_game_w: int,
                      current_game_h: int) -> None:
        """Rysuje ściągę w panelu — zakładka Gra nie miała tam nic."""
        rect = pygame.Rect(current_game_w, TAB_TOTAL_HEIGHT,
                           PANEL_W, current_game_h - TAB_TOTAL_HEIGHT)
        pygame.draw.rect(surface, _COL_PANEL_BG, rect)

        pad = 10
        y = rect.y + 6
        surface.blit(font.render("Sterowanie", True, _COL_HEADER),
                     (rect.x + pad, y))
        y += 22

        for key, action in self.CONTROLS:
            surface.blit(font.render(key, True, _COL_KEY), (rect.x + pad, y))
            surface.blit(font.render(action, True, _COL_TEXT),
                         (rect.x + pad + 42, y))
            y += 20

        y += 8
        pygame.draw.line(surface, (40, 40, 55),
                         (rect.x + pad, y), (rect.right - pad, y))
        y += 10

        surface.blit(font.render("Panel", True, _COL_HEADER), (rect.x + pad, y))
        y += 22

        for line in self.HINTS:
            if line:
                surface.blit(font.render(line, True, _COL_HINT),
                             (rect.x + pad, y))
            y += 17

        pygame.draw.rect(surface, (40, 40, 55), rect, 1)

    def draw_hud(self, surface: pygame.Surface,
                 font: pygame.font.Font,
                 state: "GameState",
                 current_game_w: int,
                 current_game_h: int) -> None:
        """Rysuje HUD na dole obszaru gry."""
        bar_h = 36
        hud_rect = pygame.Rect(0, current_game_h - bar_h, current_game_w, bar_h)

        # Półprzezroczyste tło (przez surface z alpha)
        hud_surf = pygame.Surface((hud_rect.width, hud_rect.height), pygame.SRCALPHA)
        hud_surf.fill((18, 18, 24, 200))
        surface.blit(hud_surf, hud_rect.topleft)

        pad = 8
        mid_y = hud_rect.centery

        # Monety (lewa strona)
        coins_str = f"\U0001f4b0 {short_number(state.coins)}"
        coins_surf = font.render(coins_str, True, _COL_COIN)
        surface.blit(coins_surf, (hud_rect.x + pad, mid_y - coins_surf.get_height() // 2))

        # Fala + HP okręgów (prawa strona)
        ring_hp = state.get_ring_hp()
        wave_str = f"Fala {state.wave}  |  HP okręgów: {ring_hp}"
        wave_surf = font.render(wave_str, True, _COL_WAVE)
        wave_x = hud_rect.right - wave_surf.get_width() - pad
        surface.blit(wave_surf, (wave_x, mid_y - wave_surf.get_height() // 2))

        # Pasek postępu fali (środek)
        progress = (state.rings_destroyed_this_wave /
                    max(1, state.rings_to_next_wave))
        progress = min(1.0, progress)

        bar_w = 90
        bar_h2 = 8
        bar_x = hud_rect.centerx - bar_w // 2
        bar_y = mid_y - bar_h2 // 2

        pygame.draw.rect(surface, _COL_BAR_BG,
                         pygame.Rect(bar_x, bar_y, bar_w, bar_h2),
                         border_radius=4)
        if progress > 0:
            fill_w = max(1, int(bar_w * progress))
            fill_col = _COL_BAR_FULL if progress >= 1.0 else _COL_BAR_FILL
            pygame.draw.rect(surface, fill_col,
                             pygame.Rect(bar_x, bar_y, fill_w, bar_h2),
                             border_radius=4)

        # Etykieta postępu
        prog_str = f"{state.rings_destroyed_this_wave}/{state.rings_to_next_wave}"
        prog_surf = font.render(prog_str, True, (150, 150, 170))
        surface.blit(prog_surf, prog_surf.get_rect(
            centerx=hud_rect.centerx, top=bar_y + bar_h2 + 2))
