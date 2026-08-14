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

    field.update(0.5, hp=100, wave=1)

    assert len(field.rings) == 1


def test_spawns_after_interval_once_there_is_room():
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = RING_GAP + 5.0   # zwęzi się o więcej niż odstęp

    field.update(1.0, hp=100, wave=1)

    assert len(field.rings) == 2


def test_no_spawn_while_outermost_still_fills_the_edge():
    """Odstęp między okręgami bierze się z czasu spawnu, a nie z wymuszania
    promienia po fakcie — nowy okrąg czeka, aż poprzedni zrobi mu miejsce."""
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = 1.0              # po 1 s wciąż zajmuje krawędź

    field.update(1.0, hp=100, wave=1)

    assert len(field.rings) == 1


def test_alive_rings_are_ordered_innermost_first():
    """Piłka jest wewnątrz stosu, więc dosięga wyłącznie najbliższego okręgu."""
    config, field = _field()
    config.ring_spawn_interval = 1.0
    config.ring_shrink_speed = RING_GAP + 5.0
    field.update(1.0, hp=100, wave=1)

    radii = [ring.radius for ring in field.alive()]

    assert len(radii) == 2
    assert radii == sorted(radii)


def test_faded_rings_are_dropped():
    _, field = _field()
    field.rings[0].destroy()
    field.rings[0].alpha = 0.0

    field.update(0.01, hp=100, wave=1)

    assert all(ring.alive for ring in field.rings)


def test_field_refills_when_every_ring_is_destroyed():
    """Puste pole to gra bez celu — zawsze zostaje przynajmniej jeden okrąg."""
    _, field = _field()
    field.rings[0].destroy()
    field.rings[0].alpha = 0.0

    field.update(0.01, hp=100, wave=1)

    assert len(field.alive()) == 1


def test_innermost_ring_stops_at_minimum_radius():
    config, field = _field()
    config.ring_min_radius = 30.0
    config.ring_shrink_speed = 1000.0

    field.update(1.0, hp=100, wave=1)

    assert field.innermost().radius == 30.0


def test_field_never_exceeds_max_active_rings():
    """Szybkie zwężanie zwalnia miejsce przy krawędzi na każdym tiku spawnu,
    więc bez jawnego limitu pole rośnie bez końca (przy fali 20 do 60 okręgów)."""
    config, field = _field()
    config.ring_max_active = 5
    config.ring_spawn_interval = 0.1
    config.ring_shrink_speed = 60.0

    for _ in range(2000):
        field.update(1 / 240, hp=100, wave=1)

    assert len(field.alive()) <= 5


def test_no_ring_shrinks_below_minimum_radius():
    """Klamra na samym wewnętrznym nie wystarcza — kolejne okręgi zjeżdżały
    poniżej niego i schodziły do zera."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.ring_spawn_interval = 0.5
    config.ring_shrink_speed = 200.0

    for _ in range(1000):
        field.update(1 / 240, hp=100, wave=1)

    assert all(ring.radius >= 30.0 for ring in field.alive())


def test_fresh_field_is_not_crushed():
    _, field = _field()

    assert field.is_crushed() is False


def test_field_reports_crush_when_innermost_reaches_minimum():
    """Okrąg dociśnięty do minimum nie zostawia piłce miejsca na grę."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.ring_shrink_speed = 1000.0

    field.update(1.0, hp=100, wave=1)

    assert field.is_crushed() is True


def test_cleared_field_is_not_crushed():
    """Po karze gra rusza dalej — świeże pole nie może od razu zgłaszać zduszenia."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.ring_shrink_speed = 1000.0
    field.update(1.0, hp=100, wave=1)

    field.clear(hp=100, wave=1)

    assert field.is_crushed() is False


def test_clear_leaves_one_fresh_ring_with_given_hp():
    config, field = _field()
    config.ring_shrink_speed = RING_GAP + 5.0
    config.ring_spawn_interval = 1.0
    field.update(1.0, hp=100, wave=1)

    field.clear(hp=150, wave=1)

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


def test_field_spawns_typed_rings():
    import random

    from ring_types import NORMAL

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=1,
                      rng=random.Random(7))

    assert field.rings[0].type is NORMAL


def test_field_passes_base_hp_through_to_the_ring():
    """Na fali 1 dostępny jest wyłącznie typ zwykły (mnożnik 1.0),
    więc HP okręgu musi być równe HP bazowemu."""
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=1,
                      rng=random.Random(7))

    assert field.rings[0].max_hp == 100


def test_field_uses_the_injected_rng():
    """Dwa pola z tym samym ziarnem muszą postawić tę samą sekwencję typów."""
    import random

    config_a = Config()
    field_a = RingField(config_a, (400, 400), hp=100, wave=20,
                        rng=random.Random(99))
    config_a.ring_spawn_interval = 0.5
    config_a.ring_shrink_speed = 60.0

    config_b = Config()
    field_b = RingField(config_b, (400, 400), hp=100, wave=20,
                        rng=random.Random(99))
    config_b.ring_spawn_interval = 0.5
    config_b.ring_shrink_speed = 60.0

    for _ in range(2000):
        field_a.update(1 / 240, hp=100, wave=20)
        field_b.update(1 / 240, hp=100, wave=20)

    assert ([r.type.id for r in field_a.rings]
            == [r.type.id for r in field_b.rings])


def test_high_wave_field_contains_special_rings():
    """Na fali 20 pole nie może składać się z samych zwykłych okręgów."""
    import random

    config = Config()
    config.ring_spawn_interval = 0.5
    config.ring_shrink_speed = 60.0
    field = RingField(config, (400, 400), hp=100, wave=20,
                      rng=random.Random(5))

    seen: set[str] = set()
    for _ in range(4000):
        field.update(1 / 240, hp=100, wave=20)
        seen.update(r.type.id for r in field.rings)

    assert seen - {"normal"}
