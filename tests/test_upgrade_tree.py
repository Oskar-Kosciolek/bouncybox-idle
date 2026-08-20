import pytest

from game_state import GameState
from upgrade_tree import INCOME_AT_UNLOCK, UPGRADES, Upgrade

UNBOUNDED = Upgrade("ball_damage", "Sila uderzenia", "test", "ball",
                    None, 200.0, cost_multiplier=1.6)
CAPPED = Upgrade("ball_speed", "Predkosc", "test", "ball", 5, 50.0)


def test_unbounded_upgrade_is_never_maxed():
    """Sufit poziomów oznacza skończoną pojemność wydatków, a przychód rośnie
    bez końca — po 17 minutach monety przestawały mieć zastosowanie."""
    state = GameState(upgrade_ball_damage=999)

    assert UNBOUNDED.is_maxed(state) is False


def test_capped_upgrade_still_reports_maxed():
    state = GameState(upgrade_ball_speed=5)

    assert CAPPED.is_maxed(state) is True


def test_unbounded_upgrade_can_be_bought_past_any_level():
    state = GameState(upgrade_ball_damage=40, coins=1e30)

    assert UNBOUNDED.purchase(state) is True
    assert state.upgrade_ball_damage == 41


def test_damage_cost_grows_slower_per_level_than_the_default_curve():
    """Mnożnik 1.6 zamiast 2.0 — inaczej poziomy przychodziłyby wolniej,
    niż rosną wymagania, i ulepszenie nigdy by nie nadążyło."""
    assert UNBOUNDED.cost_multiplier < CAPPED.cost_multiplier


def test_damage_upgrade_exists_in_the_tree_and_is_unbounded():
    damage = next(u for u in UPGRADES if u.id == "ball_damage")

    assert damage.max_level is None


def test_every_upgrade_id_matches_a_game_state_field():
    """Upgrade sięga po pole przez getattr(state, f"upgrade_{id}") — literówka
    w id daje AttributeError dopiero przy kliknięciu w sklepie."""
    state = GameState()

    missing = [u.id for u in UPGRADES if not hasattr(state, f"upgrade_{u.id}")]

    assert missing == []


def test_base_cost_is_minutes_times_anchor():
    """Koszt pierwszego poziomu to deklarowane minuty gry razy kotwica warstwy."""
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=2.0, unlock_wave=10)
    assert upg.base_cost == 2.0 * INCOME_AT_UNLOCK[10]


def test_base_cost_differs_per_tier_for_same_minutes():
    """Te same minuty na wyzszej warstwie kosztuja wiecej monet."""
    tier1 = Upgrade("a", "A", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=1)
    tier3 = Upgrade("b", "B", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=25)
    assert tier3.base_cost > tier1.base_cost * 100


def test_cost_at_level_still_compounds():
    upg = Upgrade("x", "X", "opis", "ball", 5, cost_minutes=1.0,
                  unlock_wave=1, cost_multiplier=2.0)
    assert upg.cost_at_level(0) == 150.0
    assert upg.cost_at_level(3) == 150.0 * 8


def test_every_upgrade_uses_a_known_tier():
    """Bramka falowa musi miec kotwice — inaczej base_cost rzuci KeyError w grze."""
    for upg in UPGRADES:
        assert upg.unlock_wave in INCOME_AT_UNLOCK


def test_unknown_unlock_wave_fails_at_validation():
    from upgrade_tree import _validate_unlock_waves
    bad = [Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=15)]
    with pytest.raises(ValueError, match="unlock_wave"):
        _validate_unlock_waves(bad)
