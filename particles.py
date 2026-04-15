import pygame
import math
import random


class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: tuple, lifetime: float) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.lifetime = lifetime
        self.age = 0.0
        self.size = random.randint(2, 4)

    def update(self, dt: float) -> bool:
        """Aktualizuje pozycję i wiek. Zwraca True dopóki cząsteczka żyje."""
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface) -> None:
        if self.age >= self.lifetime:
            return
        alpha = 1.0 - (self.age / self.lifetime)
        color = tuple(int(c * alpha) for c in self.color)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []

    def explode_ring(self, cx: float, cy: float, radius: float, color: tuple) -> None:
        """Emituje 80 cząsteczek wzdłuż okręgu o danym promieniu i środku."""
        for _ in range(80):
            angle = random.uniform(0, math.pi * 2)
            px = cx + math.cos(angle) * radius
            py = cy + math.sin(angle) * radius
            speed = random.uniform(60, 220)
            vx = math.cos(angle) * speed + random.uniform(-20, 20)
            vy = math.sin(angle) * speed + random.uniform(-20, 20)
            r = min(255, max(0, int(color[0] + random.randint(-30, 30))))
            g = min(255, max(0, int(color[1] + random.randint(-30, 30))))
            b = min(255, max(0, int(color[2] + random.randint(-30, 30))))
            lifetime = random.uniform(0.4, 1.2)
            self.particles.append(Particle(px, py, vx, vy, (r, g, b), lifetime))

    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surface)
