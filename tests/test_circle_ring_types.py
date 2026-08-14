from circle_ring import CircleRing
from config import Config
from ring_types import ARMORED, BOSS, FRAGILE, NORMAL


def test_default_ring_is_normal():
    ring = CircleRing(Config(), (400, 400), hp=100)

    assert ring.type is NORMAL


def test_armored_ring_gets_three_times_the_hp():
    """Pancerz idzie przez HP, bo ball_damage wynosi 1 i mnożnik obrażeń
    po zaokrągleniu w górę nic by nie zmienił."""
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ARMORED)

    assert ring.max_hp == 300
    assert ring.hp == 300


def test_fragile_ring_gets_a_fraction_of_the_hp():
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=FRAGILE)

    assert ring.max_hp == 15


def test_ring_hp_is_never_below_one():
    """Okrąg z zerowym HP byłby martwy w chwili postawienia."""
    ring = CircleRing(Config(), (400, 400), hp=1, ring_type=FRAGILE)

    assert ring.max_hp >= 1


def test_ring_takes_its_colour_and_thickness_from_the_type():
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=BOSS)

    assert ring.base_color == BOSS.color
    assert ring.thickness == BOSS.thickness


def test_full_health_ring_is_drawn_in_its_type_colour():
    """Interpolacja ku czerwieni musi startować z koloru typu, nie ze stałej."""
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ARMORED)

    ring._update_color()

    assert ring.color == ARMORED.color


def test_damaged_ring_shifts_towards_red():
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ARMORED)
    ring.hp = ring.max_hp // 2

    ring._update_color()

    assert ring.color[0] > ARMORED.color[0]


def test_boss_shrinks_at_half_speed():
    config = Config()
    config.ring_shrink_speed = 100.0
    normal = CircleRing(config, (400, 400), hp=100)
    boss = CircleRing(config, (400, 400), hp=100, ring_type=BOSS)
    start = normal.radius

    normal.update(1.0)
    boss.update(1.0)

    assert start - normal.radius == 100.0
    assert start - boss.radius == 50.0


def test_new_ring_has_no_split_resolved_yet():
    ring = CircleRing(Config(), (400, 400), hp=100)

    assert ring.split_resolved is False
