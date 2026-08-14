import pygame

from circle_ring import CircleRing
from config import Config
from ring_types import ARMORED, NORMAL

pygame.font.init()   # czcionki działają bez okna — set_mode nie jest potrzebne


def _draw(ring_type, font) -> bytes:
    """Rysuje okrąg danego typu na czystą powierzchnię i zwraca jej piksele."""
    surface = pygame.Surface((400, 400))
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ring_type)
    ring.radius = 80.0
    ring.draw(surface, font)
    return pygame.image.tobytes(surface, "RGB")


def test_ring_draws_without_a_font():
    """main.py podaje czcionkę, ale parametr jest opcjonalny — brak czcionki
    nie może wywalić rysowania."""
    pixels = _draw(ARMORED, None)

    assert pixels != pygame.image.tobytes(pygame.Surface((400, 400)), "RGB")


def test_font_adds_a_label_for_named_types():
    font = pygame.font.SysFont("segoeui", 13)

    assert _draw(ARMORED, font) != _draw(ARMORED, None)


def test_font_changes_nothing_for_the_plain_ring():
    """Zwykły okrąg ma pustą nazwę — nie dostaje etykiety, więc obecność
    czcionki nie może zmienić ani jednego piksela."""
    font = pygame.font.SysFont("segoeui", 13)

    assert _draw(NORMAL, font) == _draw(NORMAL, None)
