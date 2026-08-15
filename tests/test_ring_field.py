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


def test_minimum_radius_is_what_triggers_the_crush():
    """Bez karencji zduszenie zależy wyłącznie od promienia — to on jest
    progiem, a crush_grace tylko odracza wykonanie kary."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.crush_grace = 0.0
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


def _splitting_ring(field, radius: float):
    """Podmienia jedyny okrąg pola na dzielący się o zadanym promieniu."""
    from ring_types import SPLITTING

    ring = field.rings[0]
    ring.type = SPLITTING
    ring.radius = radius
    return ring


def test_destroyed_splitting_ring_spawns_two_children():
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    assert len(field.alive()) == 2


def test_children_appear_inside_the_parent_one_gap_apart():
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    radii = sorted(r.radius for r in field.alive())
    assert radii == [220.0 - 2 * RING_GAP, 220.0 - RING_GAP]


def test_children_are_ordinary_rings():
    """Inaczej podział kaskadowałby w nieskończoność."""
    from ring_types import NORMAL

    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    assert len(field.alive()) == 2
    assert all(r.type is NORMAL for r in field.alive())


def test_no_child_is_born_already_crushed():
    """Dziecko poniżej ring_min_radius natychmiast wywołałoby karę."""
    config, field = _field()
    config.ring_min_radius = 30.0
    ring = _splitting_ring(field, radius=100.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    # Miejsce starcza tylko na jedno dziecko: 100-35=65 mieści się,
    # 100-70=30 wypadłoby dokładnie na progu zduszenia.
    assert [r.radius for r in field.alive()] == [100.0 - RING_GAP]


def test_splitting_ring_with_no_room_dies_without_children():
    config, field = _field()
    config.ring_min_radius = 30.0
    ring = _splitting_ring(field, radius=50.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    # Zostaje wyłącznie okrąg dostawiony regułą "puste pole to gra bez celu"
    assert all(r.radius == config.ring_start_radius for r in field.alive())


def test_split_happens_only_once():
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)
    count_after_first = len(field.rings)
    field.update(1 / 240, hp=100, wave=6)

    # martwy rodzic (jeszcze nie wyblakł) + dwoje dzieci
    assert count_after_first == 3
    assert len(field.rings) == count_after_first


def test_split_also_fires_for_rings_killed_outside_the_collision_loop():
    """Bomba woła ring.destroy() z zupełnie innego miejsca w main.py —
    podział musi zadziałać i wtedy."""
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)

    ring.destroy()          # dokładnie to, co robi power-up bomba
    field.update(1 / 240, hp=100, wave=6)

    assert len(field.alive()) == 2


def test_boss_appears_on_every_tenth_wave():
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=10,
                      rng=random.Random(3))

    assert field.rings[0].type.id == "boss"


def test_no_boss_on_ordinary_waves():
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=9,
                      rng=random.Random(3))

    assert field.rings[0].type.id != "boss"


def test_only_one_boss_per_visit_to_a_boss_wave():
    import random

    config = Config()
    config.ring_spawn_interval = 0.1
    config.ring_shrink_speed = 60.0
    field = RingField(config, (400, 400), hp=100, wave=10,
                      rng=random.Random(3))

    for _ in range(2000):
        field.update(1 / 240, hp=100, wave=10)

    assert sum(1 for r in field.rings if r.type.id == "boss") == 1


def test_boss_returns_after_losing_and_regaining_the_wave():
    """Zduszenie przez bossa cofa gracza na falę 9. Po powrocie na 10 boss
    musi czekać ponownie — inaczej gracz mijałby go bez walki na zawsze."""
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=10,
                      rng=random.Random(3))

    field.clear(hp=100, wave=9)     # kara za zduszenie
    field.clear(hp=100, wave=10)    # gracz odbudował falę

    assert field.rings[0].type.id == "boss"


def test_ring_at_minimum_is_not_crushed_immediately():
    """Karencja daje piłce czas na dobicie dociśniętego okręgu. Przy minimalnym
    promieniu piłka odbija się kilka razy na sekundę, więc te kilka sekund
    wystarcza na fali 1 — i już nie wystarcza od fali 2."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.crush_grace = 6.0
    config.ring_shrink_speed = 1000.0

    field.update(1.0, hp=100, wave=1)

    assert field.is_crushed() is False


def test_crush_fires_once_the_grace_period_runs_out():
    config, field = _field()
    config.ring_min_radius = 30.0
    config.crush_grace = 1.0
    config.ring_shrink_speed = 1000.0
    field.update(1.0, hp=100, wave=1)          # dojeżdża do minimum

    for _ in range(300):                        # 1,25 s na minimum
        field.update(1 / 240, hp=100, wave=1)

    assert field.is_crushed() is True


def test_next_ring_gets_a_full_grace_period_of_its_own():
    """Gracz, który zdążył dobić dociśnięty okrąg, nie może zostać zduszony
    resztką karencji po poprzednim."""
    config, field = _field()
    config.ring_min_radius = 30.0
    config.crush_grace = 1.0
    config.ring_shrink_speed = 0.0              # nic się samo nie zwęża
    field.rings[0].radius = 30.0

    for _ in range(300):
        field.update(1 / 240, hp=100, wave=1)
    assert field.is_crushed() is True

    field.innermost().destroy()                 # gracz dobija dociśnięty
    field.update(1 / 240, hp=100, wave=1)       # dosypka stawia nowy
    field.innermost().radius = 30.0             # nowy też dojeżdża do minimum
    field.update(1 / 240, hp=100, wave=1)

    assert field.is_crushed() is False
