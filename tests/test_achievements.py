from achievements import ACHIEVEMENTS, check_achievements
from game_state import GameState
from upgrade_tree import UPGRADES


def _state_with_every_upgrade_bought(unbounded_level: int = 1) -> GameState:
    """Stan, w którym każde ulepszenie z sufitem jest na maksie, a każde
    bez sufitu ma `unbounded_level` poziomów."""
    state = GameState()
    for upg in UPGRADES:
        level = upg.max_level if upg.max_level is not None else unbounded_level
        setattr(state, f"upgrade_{upg.id}", level)
    return state


def test_check_achievements_survives_an_upgrade_without_a_level_cap():
    """Regresja: `upgrades_all` porównywał poziom z `max_level`, a ulepszenie
    bez sufitu ma tam None — gra wywalała się przy zakupie, który jako
    pierwszy przepchnął generator `all()` aż do `ball_damage`."""
    state = _state_with_every_upgrade_bought()

    check_achievements(state)   # nie może rzucić TypeError


def test_buying_every_upgrade_unlocks_the_completionist_achievement():
    """Ulepzenie bez sufitu nigdy nie jest "na maksie", więc "Kup wszystkie
    ulepszenia" liczy je jako kupione od pierwszego poziomu — inaczej
    osiągnięcia nie dałoby się zdobyć nigdy."""
    state = _state_with_every_upgrade_bought()

    check_achievements(state)

    assert "upgrades_all" in state.achievements_unlocked


def test_an_unbought_unbounded_upgrade_leaves_the_achievement_locked():
    state = _state_with_every_upgrade_bought(unbounded_level=0)

    check_achievements(state)

    assert "upgrades_all" not in state.achievements_unlocked


def test_a_partly_bought_tree_leaves_the_achievement_locked():
    state = _state_with_every_upgrade_bought()
    state.upgrade_hole_count = 1

    check_achievements(state)

    assert "upgrades_all" not in state.achievements_unlocked


def test_every_achievement_id_is_handled_by_check():
    """`check` to łańcuch if/elif kończący się `return False` — literówka w id
    dawałaby osiągnięcie, którego nie da się zdobyć, bez żadnego błędu."""
    state = _state_with_every_upgrade_bought(unbounded_level=99)
    state.rings_destroyed = 10_000
    state.wave = 100
    state.prestige_count = 50
    state.achievement_coins_earned = 1e9   # coins_* czytają ten licznik, nie total

    unlocked = {a.id for a in check_achievements(state)}

    assert unlocked == {a.id for a in ACHIEVEMENTS}
