import pygame
import math
import random
from config import Config


class CircleRing:
    def __init__(self, config: Config, window_size: tuple, hp: int = 100) -> None:
        self.config = config
        self.cx = window_size[0] / 2
        self.cy = window_size[1] / 2
        self.radius: float = config.ring_start_radius
        self.alive = True
        self.thickness = 4
        self.max_hp: int = hp
        self.hp: int = hp
        self.base_color = (60, 120, 200)
        self.color = self.base_color   # zmienia się z HP
        self.exploded = False  # flaga — cząsteczki emitowane tylko raz
        self.gold_multiplier: float = 1.0

        # Fade out po zniszczeniu
        self.alpha: float = 255.0

        # Wygeneruj dziury równomiernie rozłożone, z losowym przesunięciem całości
        self.holes: list[float] = []
        if config.hole_count > 0:
            step = 360.0 / config.hole_count
            offset = random.uniform(0, 360)
            for i in range(config.hole_count):
                self.holes.append((offset + i * step) % 360)

    def hit(self, damage: int = 10) -> bool:
        """Wywołaj przy odbiciu piłki od okręgu.
        Zwraca True jeśli okrąg zniszczony przez ścieranie HP."""
        self.hp = max(0, self.hp - damage)
        self._update_color()
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def destroy(self) -> None:
        """Wywołaj gdy piłka trafi w dziurę — natychmiastowe zniszczenie."""
        self.hp = 0
        self.alive = False

    def _update_color(self) -> None:
        """Kolor zmienia się od bazowego (niebieski) do czerwonego w miarę tracenia HP.
        Pełne HP = (60, 120, 200), martwe = (220, 60, 60)."""
        ratio = self.hp / self.max_hp  # 1.0 = pełne HP, 0.0 = martwe
        r = int(60 + (220 - 60) * (1.0 - ratio))
        g = int(120 * ratio)
        b = int(200 * ratio)
        self.color = (r, g, b)

    def update(self, dt: float, speed_multiplier: float = 1.0) -> None:
        if not self.alive:
            self.alpha = max(0.0, self.alpha - 400 * dt)
            return

        if self.config.hole_moving:
            self.holes = [(h + self.config.hole_move_speed * dt) % 360
                          for h in self.holes]

        # Zmniejszanie — współczynnik prędkości (np. 0.05 gdy ice aktywny)
        self.radius -= self.config.ring_shrink_speed * speed_multiplier * dt

    def is_point_in_hole(self, angle_deg: float) -> bool:
        """Sprawdź czy kąt mieści się w którejś dziurze."""
        half = self.config.hole_size / 2
        for hole in self.holes:
            # Różnica kątów znormalizowana do zakresu -180..180
            diff = (angle_deg - hole + 180) % 360 - 180
            if abs(diff) <= half:
                return True
        return False

    def check_collision(self, ball) -> bool:
        """
        Sprawdza kolizję piłki z okręgiem.
        Zwraca True jeśli nastąpiło odbicie od pełnej części.
        Jeśli piłka trafiła w dziurę — niszczy okrąg natychmiast, zwraca False.
        Odbicie od pełnej części zadaje 10 obrażeń; przy HP <= 0 okrąg zniszczony.
        """
        if not self.alive:
            return False

        dx = ball.x - self.cx
        dy = ball.y - self.cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 0.001:
            return False

        # Kolizja gdy piłka dotyka powierzchni okręgu od wewnątrz lub zewnątrz
        if abs(dist - self.radius) > ball.radius + self.thickness:
            return False

        angle = math.degrees(math.atan2(dy, dx)) % 360

        if self.is_point_in_hole(angle):
            # Dziura — natychmiastowe zniszczenie
            self.destroy()
            return False

        if ball.collision_cooldown > 0:
            return False

        # Normalna zawsze skierowana OD środka okręgu DO piłki
        nx = dx / dist
        ny = dy / dist

        # Piłka wewnątrz okręgu — wypchnij do środka (zmniejsz dist do radius - ball.radius - 1)
        if dist < self.radius:
            ball.x = self.cx + nx * (self.radius - ball.radius - self.thickness - 1)
            ball.y = self.cy + ny * (self.radius - ball.radius - self.thickness - 1)
            # Odbij do środka: normalna wskazuje do środka = -nx, -ny
            ball.bounce_radial(-nx, -ny)
        else:
            # Piłka na zewnątrz — wypchnij na zewnątrz
            ball.x = self.cx + nx * (self.radius + ball.radius + self.thickness + 1)
            ball.y = self.cy + ny * (self.radius + ball.radius + self.thickness + 1)
            ball.bounce_radial(nx, ny)

        # Odbicie zadaje obrażenia
        self.hit(self.config.ball_damage)

        return True

    def is_faded(self) -> bool:
        """Zwraca True gdy okrąg jest martwy i całkowicie przezroczysty."""
        return not self.alive and self.alpha <= 0

    def draw(self, surface: pygame.Surface) -> None:
        if self.alpha <= 0:
            return

        # Przyciemnij kolor proporcjonalnie do alpha
        if not self.alive:
            factor = self.alpha / 255.0
            color = tuple(int(c * factor) for c in self.color)
        else:
            color = self.color

        # Rysuj okrąg punkt po punkcie z pominięciem dziur
        angle = 0.0
        while angle < 360.0:
            if not self.is_point_in_hole(angle):
                rad = math.radians(angle)
                px = int(self.cx + math.cos(rad) * self.radius)
                py = int(self.cy + math.sin(rad) * self.radius)
                pygame.draw.circle(surface, color, (px, py), self.thickness)
            angle += 1.0

        # Pasek HP: poziomy prostokąt pod okręgiem (tylko gdy żywy)
        if self.alive and self.max_hp > 0:
            bar_w = 60
            bar_h = 4
            bx = int(self.cx - bar_w // 2)
            by = int(self.cy + self.radius + 8)
            pygame.draw.rect(surface, (50, 50, 65), (bx, by, bar_w, bar_h))
            fill_w = max(0, int(bar_w * self.hp / self.max_hp))
            if fill_w > 0:
                pygame.draw.rect(surface, self.color, (bx, by, fill_w, bar_h))
