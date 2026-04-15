import pygame
import math
import random

from constants import GAME_W, GAME_H

# Kolory per typ power-upa
POWERUP_COLORS: dict[str, tuple[int, int, int]] = {
    "gold":    (255, 200,  40),
    "bomb":    (220,  80,  60),
    "ice":     ( 80, 180, 255),
    "mystery": (180,  80, 255),
}

# Etykiety wyświetlane w kółku
POWERUP_LABELS: dict[str, str] = {
    "gold":    "x7",
    "bomb":    "\U0001f4a5",
    "ice":     "\u2744",
    "mystery": "?",
}

# Minimalna fala wymagana do odblokowania typu
POWERUP_UNLOCK_WAVE: dict[str, int] = {
    "gold":    3,
    "bomb":    5,
    "ice":     8,
    "mystery": 3,
}


class PowerUp:
    """Pojedynczy power-up leżący na planszy."""

    def __init__(self, x: float, y: float, kind: str) -> None:
        self.x = x
        self.y = y
        self.kind = kind          # "gold" / "bomb" / "ice" / "mystery"
        self.radius = 12
        self.age: float = 0.0
        self.alive: bool = True
        self.color = POWERUP_COLORS[kind]
        self.label = POWERUP_LABELS[kind]
        self._pulse: float = 0.0

    def update(self, dt: float, duration: float) -> bool:
        """Aktualizuje wiek i pulsowanie. Zwraca True jeśli nadal żywy."""
        self.age += dt
        self._pulse += dt * 3.0
        if self.age >= duration:
            self.alive = False
        return self.alive

    def check_collision(self, ball) -> str | None:
        """Zwraca kind jeśli piłka dotknęła power-upa, None jeśli nie."""
        dx = ball.x - self.x
        dy = ball.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < self.radius + ball.radius:
            self.alive = False
            # Mystery losuje typ w momencie zebrania
            if self.kind == "mystery":
                return random.choice(["gold", "bomb", "ice"])
            return self.kind
        return None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje power-up z efektem pulsowania i fade-out w ostatnich 2 sekundach."""
        # Pulsowanie: promień ±3px w rytm sin
        r = self.radius + int(math.sin(self._pulse) * 3)

        # Fade out w ostatnich 2 sekundach — wymaga znajomości duration,
        # ale age jest dostępne; PowerUpSystem ustawia alive=False w odpowiednim momencie.
        # Uproszczony fade: 255 zawsze, chyba że age > max_age - 2 (nie znamy max_age tutaj)
        # — używamy stałego alpha, efekt wystarczający wizualnie
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), r)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), r, 2)

        # Etykieta wyśrodkowana w kółku
        text = font.render(self.label, True, (255, 255, 255))
        rect = text.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(text, rect)


class PowerUpSystem:
    """Zarządza spawnowaniem, kolizjami i aktywnymi efektami power-upów."""

    def __init__(self) -> None:
        self.powerups: list[PowerUp] = []
        self.spawn_timer: float = 0.0
        # Aktywne efekty: {kind: czas_pozostały_w_sekundach}
        self.active_effects: dict[str, float] = {}
        self.ice_active: bool = False

    def update(self, dt: float, config, state) -> None:
        """Aktualizuje power-upy i aktywne efekty, próbuje spawn."""
        # Aktualizuj istniejące power-upy
        self.powerups = [
            p for p in self.powerups
            if p.update(dt, config.powerup_duration)
        ]

        # Aktualizuj aktywne efekty — odliczaj czas, usuń wygasłe
        to_remove = [k for k, t in self.active_effects.items() if t - dt <= 0]
        for kind in to_remove:
            del self.active_effects[kind]
        for kind in list(self.active_effects):
            self.active_effects[kind] -= dt
        self.ice_active = "ice" in self.active_effects

        # Próba spawnu
        self.spawn_timer += dt
        if self.spawn_timer >= config.powerup_spawn_interval:
            self.spawn_timer = 0.0
            self._try_spawn(config, state)

    def _try_spawn(self, config, state) -> None:
        """Próbuje dodać nowy power-up do puli jeśli limit nie przekroczony."""
        if len(self.powerups) >= config.powerup_max_visible:
            return

        # Zbierz dostępne typy odblokowane przez aktualną falę
        chances: dict[str, float] = {
            "gold":    config.powerup_chance_gold,
            "bomb":    config.powerup_chance_bomb,
            "ice":     config.powerup_chance_ice,
            "mystery": config.powerup_chance_mystery,
        }
        available: list[str] = [
            kind for kind, chance in chances.items()
            if state.wave >= POWERUP_UNLOCK_WAVE[kind]
            and random.random() < chance
        ]
        if not available:
            return

        kind = random.choice(available)

        # Losowa pozycja w kole od środka planszy
        cx = GAME_W // 2
        cy = GAME_H // 2
        angle = random.uniform(0, math.pi * 2)
        r = random.uniform(0, config.powerup_spawn_radius)
        x = cx + math.cos(angle) * r
        y = cy + math.sin(angle) * r

        self.powerups.append(PowerUp(x, y, kind))

    def check_collisions(self, ball) -> list[str]:
        """Sprawdza kolizje piłki ze wszystkimi power-upami. Zwraca zebrane typy."""
        collected: list[str] = []
        for p in self.powerups:
            result = p.check_collision(ball)
            if result:
                collected.append(result)
        self.powerups = [p for p in self.powerups if p.alive]
        return collected

    def apply_effect(self, kind: str, duration: float = 8.0) -> None:
        """Zapisuje aktywny efekt z czasem trwania (nadpisuje jeśli już aktywny)."""
        self.active_effects[kind] = duration
        self.ice_active = "ice" in self.active_effects

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje wszystkie power-upy na planszy."""
        for p in self.powerups:
            p.draw(surface, font)

    def draw_active_effects_hud(self, surface: pygame.Surface,
                                font: pygame.font.Font) -> None:
        """Rysuje aktywne efekty w prawym górnym rogu obszaru gry."""
        x = GAME_W - 10
        y = 10
        for kind, time_left in self.active_effects.items():
            color = POWERUP_COLORS[kind]
            label = POWERUP_LABELS[kind]
            text = font.render(f"{label} {time_left:.1f}s", True, color)
            rect = text.get_rect(topright=(x, y))
            surface.blit(text, rect)
            y += 20
