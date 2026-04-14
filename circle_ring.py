import pygame
import math
import random
from config import Config


class CircleRing:
    def __init__(self, config: Config, window_size: tuple) -> None:
        self.config = config
        self.cx = window_size[0] / 2
        self.cy = window_size[1] / 2
        self.radius: float = config.ring_start_radius
        self.alive = True
        self.thickness = 4
        self.color = (60, 120, 200)
        self.exploded = False  # flaga — cząsteczki emitowane tylko raz

        # Fade out po zniszczeniu
        self.alpha: float = 255.0

        # Wygeneruj dziury równomiernie rozłożone, z losowym przesunięciem całości
        self.holes: list[float] = []
        step = 360.0 / config.hole_count
        offset = random.uniform(0, 360)
        for i in range(config.hole_count):
            self.holes.append((offset + i * step) % 360)

    def update(self, dt: float) -> None:
        if not self.alive:
            self.alpha = max(0.0, self.alpha - 400 * dt)
            return

        if self.config.hole_moving:
            self.holes = [(h + self.config.hole_move_speed * dt) % 360
                          for h in self.holes]

        # Zmniejszanie — limit przekazywany z zewnątrz
        self.radius -= self.config.ring_shrink_speed * dt

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
        Jeśli piłka trafiła w dziurę — niszczy okrąg, zwraca False.
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
            self.alive = False
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
