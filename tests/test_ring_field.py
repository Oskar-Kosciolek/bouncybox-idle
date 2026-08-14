from config import Config
from ring_field import RING_GAP, RingField


def _field() -> tuple[Config, RingField]:
    """Pole okręgów na planszy 400x400 — środek (200, 200), start 220 px."""
    config = Config()
    return config, RingField(config, (400, 400), hp=100)


def test_field_starts_with_one_ring():
    _, field = _field()

    assert len(field.rings) == 1


def test_no_spawn_before_interval_elapses():
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = 40.0

    field.update(0.5, hp=100)

    assert len(field.rings) == 1


def test_spawns_after_interval_once_there_is_room():
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = RING_GAP + 5.0   # zwęzi się o więcej niż odstęp

    field.update(1.0, hp=100)

    assert len(field.rings) == 2


def test_no_spawn_while_outermost_still_fills_the_edge():
    """Odstęp między okręgami bierze się z czasu spawnu, a nie z wymuszania
    promienia po fakcie — nowy okrąg czeka, aż poprzedni zrobi mu miejsce."""
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = 1.0              # po 1 s wciąż zajmuje krawędź

    field.update(1.0, hp=100)

    assert len(field.rings) == 1


def test_alive_rings_are_ordered_innermost_first():
    """Piłka jest wewnątrz stosu, więc dosięga wyłącznie najbliższego okręgu."""
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = RING_GAP + 5.0
    field.update(1.0, hp=100)

    radii = [ring.radius for ring in field.alive()]

    assert len(radii) == 2
    assert radii == sorted(radii)


def test_faded_rings_are_dropped():
    _, field = _field()
    field.rings[0].destroy()
    field.rings[0].alpha = 0.0

    field.update(0.01, hp=100)

    assert all(ring.alive for ring in field.rings)


def test_field_refills_when_every_ring_is_destroyed():
    """Puste pole to gra bez celu — zawsze zostaje przynajmniej jeden okrąg."""
    _, field = _field()
    field.rings[0].destroy()
    field.rings[0].alpha = 0.0

    field.update(0.01, hp=100)

    assert len(field.alive()) == 1


def test_innermost_ring_stops_at_minimum_radius():
    config, field = _field()
    config.ring_min_radius = 30.0
    config.ring_shrink_speed = 1000.0

    field.update(1.0, hp=100)

    assert field.innermost().radius == 30.0


def test_field_never_exceeds_max_active_rings():
    """Szybkie zwężanie zwalnia miejsce przy krawędzi na każdym tiku spawnu,
    więc bez jawnego limitu pole rośnie bez końca (przy fali 20 do 60 okręgów)."""
    config, field = _field()
    config.ring_max_active = 5
    config.ring_spawn_interval = 0.1
    config.ring_shrink_speed = 60.0

    for _ in range(2000):
        field.update(1 / 240, hp=100)

    assert len(field.alive()) <= 5


def test_no_ring_shrinks_below_minimum_radius():
    """Klamra na samym wewnętrznym nie wystarcza — kolejne okręgi zjeżdżały
    poniżej niego i schodziły do zera."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.ring_spawn_interval = 0.5
    config.ring_shrink_speed = 200.0

    for _ in range(1000):
        field.update(1 / 240, hp=100)

    assert all(ring.radius >= 30.0 for ring in field.alive())


def test_clear_leaves_one_fresh_ring_with_given_hp():
    config, field = _field()
    config.ring_shrink_speed = RING_GAP + 5.0
    config.ring_spawn_interval = 1.0
    field.update(1.0, hp=100)

    field.clear(hp=150)

    assert len(field.rings) == 1
    assert field.rings[0].radius == config.ring_start_radius
    assert field.rings[0].max_hp == 150


def test_recenter_moves_every_ring():
    """Po zmianie rozmiaru okna okręgi mają trafić do nowego środka."""
    _, field = _field()

    field.recenter((800, 600))

    assert field.rings
    assert all(ring.cx == 400 and ring.cy == 300 for ring in field.rings)


def test_innermost_returns_none_for_empty_field():
    _, field = _field()
    field.rings.clear()

    assert field.innermost() is None
