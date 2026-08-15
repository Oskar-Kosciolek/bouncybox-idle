from config import MAX_RING_SHRINK_SPEED, Config
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


def test_max_hole_size_is_recomputed_not_accumulated():
    """Baza 10° + 5x10° z ulepszeń + 5x8° z prestige = 100°, niezależnie od
    tego, ile razy apply_upgrades zostanie wywołane."""
    config = Config()
    state = GameState()
    state.upgrade_hole_size = 5
    state.prestige_hole_size = 5

    for _ in range(20):          # 20 zakupów/awansów fali
        config.apply_upgrades(state)

    assert config.hole_size == 100.0


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

    assert config.hole_count == 1 + 2   # baza + poziomy ulepszenia


def test_fresh_game_ring_has_a_hole():
    """Bez dziury świeży gracz nie zniszczy żadnego okręgu: przy 1 obrażeniu
    na odbicie piłka nie zdejmie 100 HP, zanim stos zdusi ją na minimum.
    Zero monet oznacza zero ulepszeń, czyli grę zablokowaną na starcie."""
    config = Config()

    config.apply_upgrades(GameState())

    assert config.hole_count >= 1
    assert config.hole_size > 0.0


def test_maxed_hole_upgrades_still_leave_a_solid_arc():
    """Okrąg w 100% złożony z dziury ginie od pierwszego dotknięcia — HP,
    pancerz i boss przestają wtedy cokolwiek znaczyć na końcu progresji."""
    config = Config()
    state = GameState(upgrade_hole_size=5, upgrade_hole_count=3,
                      prestige_hole_size=5)

    config.apply_upgrades(state)

    assert config.hole_count * config.hole_size < 360.0


def test_hole_cap_does_not_touch_early_upgrades():
    """Sufit ma działać dopiero na końcu drzewka, nie odbierać pierwszych zakupów."""
    config = Config()

    config.apply_upgrades(GameState(upgrade_hole_size=2))

    assert config.hole_size == 10.0 + 2 * 10.0


def test_shrink_speed_stops_growing_at_high_waves():
    """Bez sufitu okrąg na fali 30 żyje 1,6 s i daje piłce 3 odbicia zamiast
    kilkunastu. Prędkość zwężania sterowała kiedyś samym tempem gry, ale po
    wprowadzeniu zduszenia steruje też śmiertelnością — i rosła bez granic."""
    config = Config()

    config.apply_upgrades(GameState(wave=100))

    assert config.ring_shrink_speed == MAX_RING_SHRINK_SPEED


def test_shrink_speed_still_grows_on_early_waves():
    """Sufit nie może spłaszczyć trudności od samego początku."""
    early = Config()
    early.apply_upgrades(GameState(wave=2))
    later = Config()
    later.apply_upgrades(GameState(wave=6))

    assert later.ring_shrink_speed > early.ring_shrink_speed
