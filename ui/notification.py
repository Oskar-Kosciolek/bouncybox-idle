import pygame


class NotificationSystem:
    """System powiadomień — wyświetla krótkie komunikaty z fade out."""

    def __init__(self) -> None:
        # Każde powiadomienie to słownik: text, color, age, lifetime
        self.notifications: list[dict] = []

    def add(self, text: str,
            color: tuple[int, int, int] = (255, 220, 80),
            lifetime: float = 3.0) -> None:
        """Dodaje nowe powiadomienie do kolejki."""
        self.notifications.append({
            "text": text,
            "color": color,
            "age": 0.0,
            "lifetime": lifetime,
        })

    def update(self, dt: float) -> None:
        """Aktualizuje wiek powiadomień i usuwa wygasłe."""
        for n in self.notifications:
            n["age"] += dt
        self.notifications = [
            n for n in self.notifications if n["age"] < n["lifetime"]
        ]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Rysuje aktywne powiadomienia w lewym górnym rogu obszaru gry."""
        x = 10
        y = 10
        for n in self.notifications[:5]:
            # Fade out w ostatnich 0.8 sekundy życia
            time_left = n["lifetime"] - n["age"]
            alpha = 1.0 if time_left >= 0.8 else time_left / 0.8
            color = tuple(int(c * alpha) for c in n["color"])
            text_surf = font.render(n["text"], True, color)
            surface.blit(text_surf, (x, y))
            y += 20
