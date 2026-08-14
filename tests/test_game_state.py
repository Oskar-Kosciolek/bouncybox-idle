from game_state import GameState


def test_crush_lowers_wave_by_one():
    state = GameState(wave=7)

    state.on_crushed()

    assert state.wave == 6


def test_crush_never_drops_below_wave_one():
    """Fala 0 dałaby zerowe HP okręgów i ujemną trudność."""
    state = GameState(wave=1)

    state.on_crushed()

    assert state.wave == 1


def test_crush_resets_progress_towards_next_wave():
    state = GameState(wave=5, rings_destroyed_this_wave=4)

    state.on_crushed()

    assert state.rings_destroyed_this_wave == 0


def test_crush_recomputes_rings_needed_for_next_wave():
    """Próg awansu należy do fali, więc po jej utracie musi zejść razem z nią."""
    state = GameState(wave=5)

    state.on_crushed()

    assert state.rings_to_next_wave == 5 + 4 * 2


def test_crush_leaves_coins_and_upgrades_untouched():
    """Kara ma cofać trudność, a nie kasować dorobek gracza."""
    state = GameState(wave=5, coins=900.0, upgrade_ball_speed=3)
    state.achievements_unlocked = {"wave_5"}

    state.on_crushed()

    assert state.coins == 900.0
    assert state.upgrade_ball_speed == 3
    assert state.achievements_unlocked == {"wave_5"}


def test_crush_leaves_prestige_progress_untouched():
    state = GameState(wave=5, prestige_count=2, prestige_crystals=7)

    state.on_crushed()

    assert state.prestige_count == 2
    assert state.prestige_crystals == 7


def test_ring_payout_scales_with_type_multiplier():
    plain = GameState(wave=1)
    fancy = GameState(wave=1)

    base = plain.on_ring_destroyed()
    boosted = fancy.on_ring_destroyed(type_multiplier=2.5)

    assert boosted == base * 2.5


def test_gold_and_type_multipliers_stack():
    """Złoty power-up na pancernym ma dać 7 x 2.5, nie jedno z dwóch."""
    plain = GameState(wave=1)
    both = GameState(wave=1)

    base = plain.on_ring_destroyed()
    combined = both.on_ring_destroyed(gold_multiplier=7.0, type_multiplier=2.5)

    assert combined == base * 7.0 * 2.5


def test_type_multiplier_defaults_to_neutral():
    without = GameState(wave=3).on_ring_destroyed()
    explicit = GameState(wave=3).on_ring_destroyed(type_multiplier=1.0)

    assert without == explicit
