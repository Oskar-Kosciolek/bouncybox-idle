import math
import random
import pygame
from config import Config


class Ball:
    def __init__(self, x: float, y: float, config: Config) -> None:
        self.config = config
        self.x = x
        self.y = y
        self.vx = config.initial_speed_x
        self.vy = config.initial_speed_y
        self.radius = config.ball_radius
        self.base_color = (230, 80, 80)
        self.color = self.base_color
        self.hit_flash: float = 0.0   # timer błysku koloru po odbiciu
        self.collision_cooldown = 0.0  # czas blokady po ostatnim odbiciu
        self._trail: list[tuple[float, float]] = []  # historia pozycji do smugi
        # Stała prędkość bazowa — utrzymywana po każdym odbiciu
        self.base_speed: float = math.sqrt(
            config.initial_speed_x ** 2 + config.initial_speed_y ** 2
        )

    def update(self, dt: float) -> None:
        # Grawitacja
        if self.config.gravity_enabled:
            self.vy += self.config.gravity_strength * dt

        self.collision_cooldown = max(0.0, self.collision_cooldown - dt)
        # Zapisz pozycję do smugi (max 20 punktów)
        self._trail.append((self.x, self.y))
        if len(self._trail) > 20:
            self._trail.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_radial(self, nx: float, ny: float) -> None:
        """Odbicie od normalnej (nx, ny) — wektor jednostkowy od środka okręgu do piłki."""
        dot = self.vx * nx + self.vy * ny
        self.vx = (self.vx - 2 * dot * nx) * self.config.restitution
        self.vy = (self.vy - 2 * dot * ny) * self.config.restitution

        # Losowe odchylenie ±12° — zapobiega zapętlonym torom
        angle = math.atan2(self.vy, self.vx)
        angle += math.radians(random.uniform(-12, 12))
        # Normalizacja do stałej prędkości bazowej
        self.vx = math.cos(angle) * self.base_speed
        self.vy = math.sin(angle) * self.base_speed

        self.collision_cooldown = 0.01
        self.hit_flash = 0.15  # 150ms błysku

    def reset(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = self.config.initial_speed_x
        self.vy = self.config.initial_speed_y
        self.collision_cooldown = 0.0
        self._trail.clear()

    def draw(self, surface: pygame.Surface, dt: float = 0.0) -> None:
        # Zaktualizuj błysk koloru
        self.hit_flash = max(0.0, self.hit_flash - dt)
        color = (255, 255, 255) if self.hit_flash > 0 else self.base_color

        # Smuga (jeśli włączona)
        if self.config.ball_trail_enabled and len(self._trail) > 1:
            for i, (tx, ty) in enumerate(self._trail):
                alpha = i / len(self._trail)
                r = int(color[0] * alpha)
                g = int(color[1] * alpha)
                b = int(color[2] * alpha)
                trail_r = max(1, int(self.radius * alpha * 0.6))
                pygame.draw.circle(surface, (r, g, b), (int(tx), int(ty)), trail_r)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.radius)
