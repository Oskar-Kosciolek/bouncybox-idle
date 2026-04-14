import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState


_COL_HUD_BG    = (18, 18, 24, 180)   # półprzezroczyste tło HUD
_COL_TEXT      = (220, 220, 240)
_COL_COIN      = (220, 200, 80)
_COL_WAVE      = (100, 180, 255)
_COL_BAR_BG    = (40, 40, 55)
_COL_BAR_FILL  = (80, 180, 100)
_COL_BAR_FULL  = (100, 220, 120)


class GameView:
    """Nakładka HUD rysowana w obszarze gry."""

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect   # obszar gry (np. 520x520)

    def draw_hud(self, surface: pygame.Surface,
                 font: pygame.font.Font,
                 state: "GameState") -> None:
        """Rysuje HUD na dole obszaru gry."""
        bar_h = 36
        hud_rect = pygame.Rect(self.rect.x, self.rect.bottom - bar_h,
                               self.rect.width, bar_h)

        # Półprzezroczyste tło (przez surface z alpha)
        hud_surf = pygame.Surface((hud_rect.width, hud_rect.height), pygame.SRCALPHA)
        hud_surf.fill((18, 18, 24, 200))
        surface.blit(hud_surf, hud_rect.topleft)

        pad = 8
        mid_y = hud_rect.centery

        # Monety (lewa strona)
        coins_str = f"\U0001f4b0 {state.coins:,.0f}"
        coins_surf = font.render(coins_str, True, _COL_COIN)
        surface.blit(coins_surf, (hud_rect.x + pad, mid_y - coins_surf.get_height() // 2))

        # Fala (prawa strona)
        wave_str = f"Fala {state.wave}"
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
