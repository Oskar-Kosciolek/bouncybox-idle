import random

from ring_types import (
    ARMORED,
    BOSS,
    FRAGILE,
    NORMAL,
    SPAWNABLE_TYPES,
    SPLITTING,
    pick_type,
)


def test_weight_is_zero_before_unlock_wave():
    """Typ niedostępny na danej fali nie może w ogóle wypaść."""
    assert ARMORED.effective_weight(3) == 0.0


def test_weight_equals_base_on_unlock_wave():
    assert ARMORED.effective_weight(4) == 1.0


def test_weight_grows_with_wave_for_special_types():
    assert ARMORED.effective_weight(20) == 1.0 + 0.25 * 16


def test_normal_weight_shrinks_with_wave():
    """Zwykły okrąg ustępuje miejsca specjalnym w miarę postępu."""
    assert NORMAL.effective_weight(20) < NORMAL.effective_weight(1)


def test_normal_weight_reaches_zero_around_wave_30():
    """Od tej fali plansza składa się wyłącznie z typów specjalnych."""
    assert NORMAL.effective_weight(29) > 0.0
    assert NORMAL.effective_weight(30) == 0.0


def test_boss_is_not_in_the_random_pool():
    """Boss stawiany jest deterministycznie, nie losowany."""
    assert BOSS not in SPAWNABLE_TYPES


def test_only_normal_can_appear_on_wave_one():
    rng = random.Random(1234)

    picked = {pick_type(1, rng).id for _ in range(200)}

    assert picked == {"normal"}


def test_wave_twenty_draws_all_unlocked_types():
    rng = random.Random(1234)

    picked = {pick_type(20, rng).id for _ in range(500)}

    assert picked == {"normal", "fragile", "armored", "splitting"}


def test_armored_is_the_most_common_type_on_wave_twenty():
    """Krzywa trudności: pancerny ma na fali 20 największą wagę (39%)."""
    rng = random.Random(1234)

    counts: dict[str, int] = {}
    for _ in range(5000):
        ring_type = pick_type(20, rng)
        counts[ring_type.id] = counts.get(ring_type.id, 0) + 1

    assert max(counts, key=counts.get) == "armored"


def test_fragile_pays_more_and_dies_faster_than_normal():
    assert FRAGILE.hp_multiplier < NORMAL.hp_multiplier
    assert FRAGILE.coin_multiplier > NORMAL.coin_multiplier


def test_splitting_ring_declares_two_children():
    assert SPLITTING.splits_into == 2


def test_boss_shrinks_slower_to_leave_time_for_the_fight():
    assert BOSS.shrink_multiplier < 1.0
