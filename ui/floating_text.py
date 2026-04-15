import pygame


class FloatingText:
    def __init__(self, x: float, y: float, text: str,
                 color: tuple = (255, 255, 255), lifetime: float = 0.8) -> None:
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = lifetime
        self.age = 0.0
        self.vy = -60.0  # unosi się w górę

    def update(self, dt: float) -> bool:
        """Aktualizuje pozycję i wiek. Zwraca True dopóki żywy."""
        self.age += dt
        self.y += self.vy * dt
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        alpha = 1.0 - (self.age / self.lifetime)
        color = tuple(int(c * alpha) for c in self.color)
        text = font.render(self.text, True, color)
        surface.blit(text, (int(self.x), int(self.y)))


class FloatingTextSystem:
    def __init__(self) -> None:
        self.texts: list[FloatingText] = []

    def add(self, x: float, y: float, text: str,
            color: tuple = (255, 255, 255), lifetime: float = 0.8) -> None:
        """Dodaje nowy pływający napis."""
        self.texts.append(FloatingText(x, y, text, color, lifetime))

    def update(self, dt: float) -> None:
        """Usuwa wygasłe napisy."""
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        for t in self.texts:
            t.draw(surface, font)
