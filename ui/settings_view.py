import pygame
from typing import Callable, TYPE_CHECKING

from confirm import ConfirmedAction
from constants import PANEL_W
from ui.tab_bar import TAB_TOTAL_HEIGHT

if TYPE_CHECKING:
    from config import Config

_COL_BG      = (24, 24, 32)
_COL_LABEL   = (200, 200, 220)
_COL_VALUE   = (220, 200,  80)
_COL_BAR_BG  = (40,  40,  55)
_COL_BAR_FG  = (80, 140, 220)
_COL_BORDER  = (40,  40,  55)
_COL_RESET       = (120,  45,  45)
_COL_RESET_ARMED = (200,  60,  60)
_COL_RESET_TEXT  = (240, 220, 220)

# (etykieta, pole w Config, min, max, czy_float)
# Uwaga: ring_shrink_speed i ring_spawn_interval są POCHODNE — apply_upgrades
# przelicza je przy każdym zakupie i awansie fali, więc suwak na nich nic nie
# trzymał. Sterujemy tu ich wejściami.
_SLIDERS: list[tuple[str, str, float, float, bool]] = [
    ("Efekty (0 = cisza)",      "sound_volume",           0.0,   1.0, True),
    ("Muzyka (0 = cisza)",      "music_volume",           0.0,   1.0, True),
    ("Karencja zduszenia (s)",  "crush_grace",            0.0,  20.0, True),
    ("Dziura x obrazen",        "hole_damage_multiplier",  1.0, 100.0, False),
    ("Zwezanie na fale",        "shrink_per_wave",        0.0,  10.0, True),
    ("Sufit zwezania",          "max_shrink_speed",       5.0, 100.0, True),
    ("Min odstep spawnu (s)",   "min_spawn_interval",     0.2,   5.0, True),
    ("Promien startowy",        "ring_start_radius",    100.0, 230.0, True),
    ("Min promien",             "ring_min_radius",       20.0, 100.0, True),
    ("Max okregow",             "ring_max_active",        1.0,  10.0, False),
    ("Czas power-upa (s)",      "powerup_duration",       3.0,  20.0, True),
    ("Max power-upow",          "powerup_max_visible",    1.0,   5.0, False),
    ("Promien spawnu PU",       "powerup_spawn_radius",  50.0, 240.0, True),
    ("Odstep spawnu PU (s)",    "powerup_spawn_interval", 3.0,  20.0, True),
    ("Szansa zloty",            "powerup_chance_gold",    0.0,   1.0, True),
    ("Szansa bomba",            "powerup_chance_bomb",    0.0,   1.0, True),
    ("Szansa lodowy",           "powerup_chance_ice",     0.0,   1.0, True),
    ("Szansa mystery",          "powerup_chance_mystery", 0.0,   1.0, True),
]

_ROW_H = 54   # wysokość jednego wiersza suwaka
_BAR_H = 10   # wysokość paska suwaka
_PAD   = 10   # padding poziomy
# Stopka z przyciskiem resetu — nie przewija się razem z suwakami, bo suwaków
# jest 18 i przycisk byłby poza ekranem dokładnie wtedy, gdy gracz go szuka.
_FOOTER_H = 46
_BTN_H    = 30


class SettingsView:
    """Widok developerski — suwaki do tuningu Config i twardy reset."""

    def __init__(self, reset_confirm: ConfirmedAction) -> None:
        self.rect: pygame.Rect | None = None
        self._dragging: int | None = None   # indeks aktualnie przeciąganego suwaka
        self.scroll: float = 0.0            # offset scrolla w pikselach
        # Współdzielony z F6 — jedno okno potwierdzenia na obie drogi.
        self.reset_confirm = reset_confirm

    # ------------------------------------------------------------------
    # Geometria
    # ------------------------------------------------------------------

    def _set_rect(self, current_game_w: int, current_game_h: int) -> None:
        self.rect = pygame.Rect(current_game_w, TAB_TOTAL_HEIGHT,
                                PANEL_W, current_game_h - TAB_TOTAL_HEIGHT)

    def slider_area(self) -> pygame.Rect:
        """Przewijalny obszar suwaków — panel bez stopki."""
        return pygame.Rect(self.rect.x, self.rect.y,
                           self.rect.width, self.rect.height - _FOOTER_H)

    def reset_btn_rect(self) -> pygame.Rect:
        """Przycisk twardego resetu w stopce."""
        return pygame.Rect(self.rect.x + _PAD,
                           self.rect.bottom - _FOOTER_H + 8,
                           self.rect.width - _PAD * 2, _BTN_H)

    def reset_btn_label(self, now: float) -> str:
        return ("NA PEWNO? (klik znow)"
                if self.reset_confirm.is_armed(now) else "RESET WSZYSTKIEGO")

    # ------------------------------------------------------------------
    # Zdarzenia
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event, config: "Config",
                     on_reset: Callable[[], None], now: float,
                     current_game_w: int, current_game_h: int) -> None:
        self._set_rect(current_game_w, current_game_h)
        if event.type == pygame.MOUSEWHEEL:
            self.scroll -= event.y * 20
            max_scroll = max(
                0.0, len(_SLIDERS) * _ROW_H - self.slider_area().height + 30)
            self.scroll = max(0.0, min(self.scroll, max_scroll))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.reset_btn_rect().collidepoint(event.pos):
                if self.reset_confirm.request(now):
                    on_reset()
                return

            # Suwaki przewijają się pod stopkę, więc trafianie w nie musi się
            # kończyć nad przyciskiem — inaczej jeden klik i kasuje postęp,
            # i po drodze przestawia balans.
            if not self.slider_area().collidepoint(event.pos):
                return

            for i in range(len(_SLIDERS)):
                bar_rect = self._bar_rect(i)
                if bar_rect.collidepoint(event.pos):
                    self._dragging = i
                    self._set_value_from_x(i, event.pos[0], config)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = None

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging is not None:
                self._set_value_from_x(self._dragging, event.pos[0], config)

    def _set_value_from_x(self, index: int, mouse_x: int, config: "Config") -> None:
        """Ustawia wartość pola config proporcjonalnie do pozycji X myszy na pasku."""
        _, field, vmin, vmax, is_float = _SLIDERS[index]
        bar_rect = self._bar_rect(index)
        ratio = (mouse_x - bar_rect.x) / max(1, bar_rect.width)
        ratio = max(0.0, min(1.0, ratio))
        raw = vmin + ratio * (vmax - vmin)
        value = raw if is_float else int(round(raw))
        setattr(config, field, value)

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             config: "Config", now: float,
             current_game_w: int, current_game_h: int) -> None:
        self._set_rect(current_game_w, current_game_h)
        pygame.draw.rect(surface, _COL_BG, self.rect)

        # Przytnij do obszaru suwaków, nie całego panelu — wiersz przewinięty
        # na sam dół wjeżdżałby inaczej pod przycisk resetu.
        old_clip = surface.get_clip()
        surface.set_clip(self.slider_area())

        header = font.render("Ustawienia (dev)", True, (120, 120, 160))
        surface.blit(header, (self.rect.x + _PAD, self.rect.y + 6))

        for i, (label, field, vmin, vmax, is_float) in enumerate(_SLIDERS):
            row_y = self.rect.y + 30 + i * _ROW_H - int(self.scroll)

            # Pomiń wiersze całkowicie poza widocznym obszarem
            if row_y + _ROW_H < self.rect.y or row_y > self.rect.bottom:
                continue

            current = getattr(config, field)

            # Etykieta
            lbl_surf = font.render(label, True, _COL_LABEL)
            surface.blit(lbl_surf, (self.rect.x + _PAD, row_y))

            # Wartość po prawej
            val_str = f"{current:.2f}" if is_float else str(int(current))
            val_surf = font.render(val_str, True, _COL_VALUE)
            surface.blit(val_surf,
                         (self.rect.right - val_surf.get_width() - _PAD, row_y))

            # Pasek suwaka
            bar_rect = self._bar_rect(i)
            pygame.draw.rect(surface, _COL_BAR_BG, bar_rect, border_radius=4)

            ratio = (current - vmin) / max(1e-6, vmax - vmin)
            ratio = max(0.0, min(1.0, ratio))
            fill_w = max(4, int(bar_rect.width * ratio))
            pygame.draw.rect(surface, _COL_BAR_FG,
                             pygame.Rect(bar_rect.x, bar_rect.y, fill_w, _BAR_H),
                             border_radius=4)

        surface.set_clip(old_clip)
        self._draw_reset_button(surface, font, now)
        pygame.draw.rect(surface, _COL_BORDER, self.rect, 1)

    def _draw_reset_button(self, surface: pygame.Surface,
                           font: pygame.font.Font, now: float) -> None:
        """Stopka: przycisk kasujący cały postęp, z potwierdzeniem."""
        btn = self.reset_btn_rect()
        armed = self.reset_confirm.is_armed(now)

        pygame.draw.rect(surface, (18, 18, 24),
                         pygame.Rect(self.rect.x, btn.y - 8,
                                     self.rect.width, _FOOTER_H))
        pygame.draw.line(surface, _COL_BORDER,
                         (self.rect.x, btn.y - 8), (self.rect.right, btn.y - 8))
        pygame.draw.rect(surface,
                         _COL_RESET_ARMED if armed else _COL_RESET,
                         btn, border_radius=4)
        label = font.render(self.reset_btn_label(now), True, _COL_RESET_TEXT)
        surface.blit(label, label.get_rect(center=btn.center))

    # ------------------------------------------------------------------
    # Pomocnicze
    # ------------------------------------------------------------------

    def _bar_rect(self, index: int) -> pygame.Rect:
        """Prostokąt paska suwaka dla danego indeksu (z uwzględnieniem scrolla)."""
        row_y = self.rect.y + 30 + index * _ROW_H - int(self.scroll)
        bar_y = row_y + 20
        return pygame.Rect(self.rect.x + _PAD, bar_y,
                           self.rect.width - _PAD * 2, _BAR_H)
