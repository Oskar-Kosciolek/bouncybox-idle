from game_state import GameState
from upgrade_tree import UPGRADES, Upgrade

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
