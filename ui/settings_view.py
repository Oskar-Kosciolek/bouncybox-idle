import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Config

_COL_BG      = (24, 24, 32)
_COL_LABEL   = (200, 200, 220)
_COL_VALUE   = (220, 200,  80)
_COL_BAR_BG  = (40,  40,  55)
_COL_BAR_FG  = (80, 140, 220)
_COL_BORDER  = (40,  40,  55)

# (etykieta, pole w Config, min, max, czy_float)
_SLIDERS: list[tuple[str, str, float, float, bool]] = [
    ("Spawn okregów (s)",       "ring_spawn_interval",    0.5,  10.0, True),
    ("Predkosc zwezania",       "ring_shrink_speed",      5.0, 100.0, True),
    ("Promien startowy",        "ring_start_radius",    100.0, 230.0, True),
    ("Min promien",             "ring_min_radius",       20.0, 100.0, True),
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


class SettingsView:
    """Widok developerski — suwaki do tuningu Config."""

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self._dragging: int | None = None   # indeks aktualnie przeciąganego suwaka
        self.scroll: float = 0.0            # offset scrolla w pikselach

    # ------------------------------------------------------------------
    # Zdarzenia
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event, config: "Config") -> None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll -= event.y * 20
            max_scroll = max(0.0, len(_SLIDERS) * _ROW_H - self.rect.height + 30)
            self.scroll = max(0.0, min(self.scroll, max_scroll))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
             config: "Config") -> None:
        pygame.draw.rect(surface, _COL_BG, self.rect)

        # Przytnij do obszaru panelu
        old_clip = surface.get_clip()
        surface.set_clip(self.rect)

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
        pygame.draw.rect(surface, _COL_BORDER, self.rect, 1)

    # ------------------------------------------------------------------
    # Pomocnicze
    # ------------------------------------------------------------------

    def _bar_rect(self, index: int) -> pygame.Rect:
        """Prostokąt paska suwaka dla danego indeksu (z uwzględnieniem scrolla)."""
        row_y = self.rect.y + 30 + index * _ROW_H - int(self.scroll)
        bar_y = row_y + 20
        return pygame.Rect(self.rect.x + _PAD, bar_y,
                           self.rect.width - _PAD * 2, _BAR_H)
