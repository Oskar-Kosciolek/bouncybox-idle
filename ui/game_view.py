import pygame
from typing import Callable, TYPE_CHECKING

from confirm import ConfirmedAction
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
_COL_SAVE      = (45, 110, 65)
_COL_RESET     = (120, 45, 45)
_COL_RESET_ARM = (200, 60, 60)
_COL_BTN_TEXT  = (235, 235, 240)
_COL_SEP       = (40, 40, 55)

_PAD     = 10
_BTN_H   = 30
_BTN_GAP = 8    # odstęp przycisku od krawędzi panelu
_HDR_H   = 20
_ROW_H   = 20
_SEP_H   = 12
_LINE_H  = 17
_TOP_GAP = 14   # odstęp treści od przycisku zapisu


class GameView:
    """Zakładka Gra: nakładka HUD nad planszą i ściąga w panelu obok."""

    # Skróty klawiszowe. Trzymane jako dane, nie wklejone w rysowanie, bo
    # test pilnuje, że pokrywają się z tabelą w README — a README już raz
    # przeżył usunięcie całej zakładki, nic o tym nie wiedząc.
    # Skróty klawiszowe. Trzymane jako dane, nie wklejone w rysowanie, bo
    # test pilnuje, że pokrywają się z tabelą w README — a README już raz
    # przeżył usunięcie całej zakładki, nic o tym nie wiedząc.
    CONTROLS: list[tuple[str, str]] = [
        ("ESC", "zapis i wyjscie"),
        ("R",   "nowa runda"),
        ("F5",  "reczny zapis"),
        ("F6",  "twardy reset"),
    ]

    # Panel ma 180 px, więc linie są łamane ręcznie — automatyczne zawijanie
    # dla czterech zdań byłoby droższe niż same zdania. Ten blok jest też
    # fizycznym rozdzielaczem: przycisk zapisu i przycisk resetu nie mogą
    # sąsiadować, bo pomyłka kosztuje cały postęp.
    ABOUT: list[str] = [
        "Pilka odbija sie w",
        "okregach z dziurami.",
        "Kliknij wezel drzewka,",
        "zeby kupic poziom.",
    ]

    def __init__(self, reset_confirm: ConfirmedAction) -> None:
        # Współdzielony z F6 — jedno okno potwierdzenia na obie drogi.
        self.reset_confirm = reset_confirm
        self.rect: pygame.Rect | None = None

    # ------------------------------------------------------------------
    # Geometria — wspólna dla rysowania i klikania
    # ------------------------------------------------------------------

    def _set_rect(self, current_game_w: int, current_game_h: int) -> None:
        self.rect = pygame.Rect(current_game_w, TAB_TOTAL_HEIGHT,
                                PANEL_W, current_game_h - TAB_TOTAL_HEIGHT)

    def save_btn_rect(self) -> pygame.Rect:
        """Przycisk ręcznego zapisu — u góry panelu."""
        return pygame.Rect(self.rect.x + _PAD, self.rect.y + _BTN_GAP,
                           self.rect.width - _PAD * 2, _BTN_H)

    def reset_btn_rect(self) -> pygame.Rect:
        """Przycisk twardego resetu — u dołu, jak najdalej od zapisu."""
        return pygame.Rect(self.rect.x + _PAD,
                           self.rect.bottom - _BTN_GAP - _BTN_H,
                           self.rect.width - _PAD * 2, _BTN_H)

    def content_bottom(self) -> int:
        """Y, na którym kończy się tekst. Liczone, nie zmierzone po fakcie —
        dopisana linia ma zderzyć się z testem, nie schować pod przyciskiem.
        """
        return (self.rect.y + _BTN_GAP + _BTN_H + _TOP_GAP
                + _HDR_H + len(self.CONTROLS) * _ROW_H
                + _SEP_H + _HDR_H + len(self.ABOUT) * _LINE_H)

    def reset_btn_label(self, now: float) -> str:
        return ("NA PEWNO? (klik znow)"
                if self.reset_confirm.is_armed(now) else "RESET WSZYSTKIEGO")

    # ------------------------------------------------------------------
    # Zdarzenia
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event,
                     on_save: Callable[[], None],
                     on_reset: Callable[[], None],
                     now: float,
                     current_game_w: int, current_game_h: int) -> None:
        """Obsługuje kliknięcia obu przycisków panelu."""
        self._set_rect(current_game_w, current_game_h)

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if self.save_btn_rect().collidepoint(event.pos):
            # Zapis niczego nie niszczy, więc nie ma czego potwierdzać.
            on_save()
            return

        if self.reset_btn_rect().collidepoint(event.pos):
            if self.reset_confirm.request(now):
                on_reset()

    # ------------------------------------------------------------------
    # Rysowanie panelu
    # ------------------------------------------------------------------

    def draw_controls(self, surface: pygame.Surface,
                      font: pygame.font.Font, now: float,
                      current_game_w: int, current_game_h: int) -> None:
        """Rysuje panel zakładki Gra: zapis, ściąga, opis, reset."""
        self._set_rect(current_game_w, current_game_h)
        rect = self.rect
        pygame.draw.rect(surface, _COL_PANEL_BG, rect)

        self._draw_button(surface, font, self.save_btn_rect(),
                          _COL_SAVE, "ZAPISZ TERAZ")

        x = rect.x + _PAD
        y = rect.y + _BTN_GAP + _BTN_H + _TOP_GAP

        surface.blit(font.render("Sterowanie", True, _COL_HEADER), (x, y))
        y += _HDR_H

        for key, action in self.CONTROLS:
            surface.blit(font.render(key, True, _COL_KEY), (x, y))
            surface.blit(font.render(action, True, _COL_TEXT), (x + 42, y))
            y += _ROW_H

        pygame.draw.line(surface, _COL_SEP,
                         (x, y + _SEP_H // 2), (rect.right - _PAD, y + _SEP_H // 2))
        y += _SEP_H

        surface.blit(font.render("O grze", True, _COL_HEADER), (x, y))
        y += _HDR_H

        for line in self.ABOUT:
            surface.blit(font.render(line, True, _COL_HINT), (x, y))
            y += _LINE_H

        self._draw_button(surface, font, self.reset_btn_rect(),
                          _COL_RESET_ARM if self.reset_confirm.is_armed(now)
                          else _COL_RESET,
                          self.reset_btn_label(now))

        pygame.draw.rect(surface, _COL_SEP, rect, 1)

    @staticmethod
    def _draw_button(surface: pygame.Surface, font: pygame.font.Font,
                     btn: pygame.Rect, color: tuple[int, int, int],
                     label: str) -> None:
        pygame.draw.rect(surface, color, btn, border_radius=4)
        text = font.render(label, True, _COL_BTN_TEXT)
        surface.blit(text, text.get_rect(center=btn.center))

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
