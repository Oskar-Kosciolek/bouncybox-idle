from config import Config
from game_state import GameState


def test_apply_upgrades_twice_gives_same_result():
    """apply_upgrades jest wołane przy każdym zakupie, awansie fali i prestige.
    Musi przeliczać wartości od zera, a nie doklejać ich do poprzednich."""
    config = Config()
    state = GameState()
    state.upgrade_hole_size = 3

    config.apply_upgrades(state)
    first_result = config.hole_size

    config.apply_upgrades(state)

    assert config.hole_size == first_result


def test_hole_never_swallows_whole_ring_at_max_upgrades():
    """Dziura 360° oznaczałaby okrąg złożony wyłącznie z dziury — piłka
    niszczyłaby go pierwszym dotknięciem. Max: 5x10° + 5x8° prestige = 90°."""
    config = Config()
    state = GameState()
    state.upgrade_hole_size = 5
    state.prestige_hole_size = 5

    for _ in range(20):          # 20 zakupów/awansów fali
        config.apply_upgrades(state)

    assert config.hole_size == 90.0


def test_shrink_speed_depends_only_on_current_wave():
    """Gracz przechodzący fale 1..10 musi mieć tę samą trudność co gracz,
    który wczytał zapis z falą 10."""
    progressed = Config()
    state = GameState()
    for wave in range(1, 11):
        state.wave = wave
        progressed.apply_upgrades(state)

    loaded = Config()
    loaded.apply_upgrades(GameState(wave=10))

    assert progressed.ring_shrink_speed == loaded.ring_shrink_speed


def test_ball_radius_grows_by_2px_per_level():
    config = Config()
    state = GameState(upgrade_ball_size=3)

    config.apply_upgrades(state)
    config.apply_upgrades(state)

    assert config.ball_radius == 5 + 3 * 2


def test_hole_count_does_not_accumulate_between_calls():
    config = Config()
    state = GameState(upgrade_hole_count=2)

    for _ in range(5):
        config.apply_upgrades(state)

    assert config.hole_count == 2
