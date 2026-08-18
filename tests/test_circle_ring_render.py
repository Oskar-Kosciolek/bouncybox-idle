import math

import pygame

from circle_ring import CircleRing
from config import Config
from ring_types import NORMAL

pygame.font.init()

SIZE = 520
CENTRE = SIZE / 2


def _ring(radius: float, hole_count: int, hole_size: float) -> CircleRing:
    config = Config()
    config.hole_count = hole_count
    config.hole_size = hole_size
    ring = CircleRing(config, (SIZE, SIZE), hp=100, ring_type=NORMAL)
    ring.radius = radius
    if hole_count:
        step = 360.0 / hole_count
        ring.holes = [(i * step) % 360 for i in range(hole_count)]
    else:
        ring.holes = []
    return ring


def _painted_near(surface: pygame.Surface, ring: CircleRing,
                  angle: float) -> bool:
    """Czy w okolicy punktu na linii okręgu cokolwiek narysowano."""
    rad = math.radians(angle)
    px = int(ring.cx + math.cos(rad) * ring.radius)
    py = int(ring.cy + math.sin(rad) * ring.radius)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if surface.get_at((px + dx, py + dy))[:3] != (0, 0, 0):
                return True
    return False


def _draw(ring: CircleRing) -> pygame.Surface:
    surface = pygame.Surface((SIZE, SIZE))
    ring.draw(surface)
    return surface


def test_solid_part_of_the_ring_is_painted_all_the_way_round():
    """Łuk narysowany z błędnym kierunkiem kąta albo złym prostokątem daje
    okrąg przesunięty lub rozerwany — obraz nadal 'jakiś' jest."""
    ring = _ring(radius=180.0, hole_count=3, hole_size=40.0)
    surface = _draw(ring)

    gaps = [a for a in range(0, 3600)
            if not ring.is_point_in_hole(a / 10)
            and not _painted_near(surface, ring, a / 10)]

    assert gaps == []


def test_holes_stay_empty():
    ring = _ring(radius=180.0, hole_count=3, hole_size=40.0)
    surface = _draw(ring)

    # Środek każdej dziury, z zapasem od krawędzi
    for hole in ring.holes:
        assert not _painted_near(surface, ring, hole)


def test_a_ring_without_holes_is_a_full_circle():
    ring = _ring(radius=150.0, hole_count=0, hole_size=0.0)
    surface = _draw(ring)

    gaps = [a for a in range(0, 360)
            if not _painted_near(surface, ring, float(a))]

    assert gaps == []


def test_a_zero_width_hole_still_leaves_a_full_circle():
    """Świeży gracz ma dokładnie taki okrąg: jedna dziura o szerokości zero.
    Zdegenerowany łuk narysowałby wtedy nic albo pełne koło raz za dużo."""
    ring = _ring(radius=150.0, hole_count=1, hole_size=0.0)
    surface = _draw(ring)

    gaps = [a for a in range(0, 360)
            if not _painted_near(surface, ring, float(a))]

    assert gaps == []


def test_band_is_centred_on_the_ring_line():
    """Prostokąt łuku musi mieć promień r+grubość, bo pygame rysuje do środka.
    Przy pomyłce pasmo przesuwa się do wewnątrz o całą swoją grubość."""
    ring = _ring(radius=150.0, hole_count=0, hole_size=0.0)
    surface = _draw(ring)

    inner = surface.get_at((int(ring.cx + ring.radius - ring.thickness + 1),
                            int(ring.cy)))[:3]
    outer = surface.get_at((int(ring.cx + ring.radius + ring.thickness - 1),
                            int(ring.cy)))[:3]

    assert inner != (0, 0, 0)
    assert outer != (0, 0, 0)


def _ring_with_holes(radius: float, holes: list[float],
                     hole_size: float) -> CircleRing:
    ring = _ring(radius, hole_count=len(holes), hole_size=hole_size)
    ring.holes = list(holes)
    return ring


def test_asymmetric_holes_land_where_they_belong():
    """Równomiernie rozłożone dziury są symetryczne względem odbicia, więc
    przepuszczają odwrócony kierunek kątów — lustrzane odcinki wypadają tam
    samo. Ekranowy Y rośnie w dół, a pygame liczy kąty przeciwnie."""
    ring = _ring_with_holes(180.0, holes=[10.0, 200.0], hole_size=30.0)
    surface = _draw(ring)

    # Margines od krawędzi dziury: sprawdzamy otoczenie 3x3 piksele, więc tuż
    # przy krawędzi łapiemy sąsiedni lity fragment. Odwrócony kierunek kątów
    # przesuwa odcinki o dziesiątki stopni, nie o ułamek.
    def near_edge(angle: float) -> bool:
        return any(abs((angle - h + 180) % 360 - 180) - 15.0 < 3.0
                   and abs((angle - h + 180) % 360 - 180) - 15.0 > -3.0
                   for h in ring.holes)

    wrong = [a / 10 for a in range(0, 3600)
             if not near_edge(a / 10)
             and ring.is_point_in_hole(a / 10) == _painted_near(
                 surface, ring, a / 10)]

    assert wrong == []


def test_a_single_hole_leaves_the_rest_of_the_ring_solid():
    """Jedna dziura zamyka okrąg sam ze sobą: odstęp do 'następnej' dziury
    liczony przez modulo daje zero i kasuje cały okrąg."""
    ring = _ring_with_holes(150.0, holes=[90.0], hole_size=60.0)
    surface = _draw(ring)

    solid = [a for a in range(0, 360)
             if not ring.is_point_in_hole(float(a))]
    unpainted = [a for a in solid if not _painted_near(surface, ring, float(a))]

    assert len(solid) > 250
    assert unpainted == []
