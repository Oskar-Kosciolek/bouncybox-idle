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
    """5x10° z ulepszeń + 5x8° z prestige = 90°, niezależnie od
    tego, ile razy apply_upgrades zostanie wywołane."""
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

    assert config.hole_count == 1 + 2   # baza + poziomy ulepszenia


def test_fresh_game_ring_has_no_usable_hole():
    """Dziura na starcie psuła balans: przy 77 odbiciach na fali 1 trafiał się
    prawie pewny darmowy zabój, więc ulepszenia dziur traciły sens. Świeży
    gracz dobija okręgi karencją przed zduszeniem, nie dziurą."""
    config = Config()

    config.apply_upgrades(GameState())

    assert config.hole_size == 0.0


def test_first_hole_size_upgrade_takes_effect_immediately():
    """Okrąg ma od startu jedną dziurę o zerowej szerokości. Bez niej pierwszy
    poziom `hole_size` byłby pustym wydatkiem, bo drzewko wymaga kupienia
    rozmiaru przed liczbą dziur, a rozmiar bez liczby nie robi nic."""
    config = Config()

    config.apply_upgrades(GameState(upgrade_hole_size=1))

    assert config.hole_count >= 1
    assert config.hole_size == 10.0


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

    assert config.hole_size == 2 * 10.0


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


def test_shrink_growth_per_wave_is_tunable():
    """Suwak ma sterować wejściem, a nie wynikiem. ring_shrink_speed jest polem
    pochodnym — apply_upgrades nadpisze każdą wartość wpisaną w nie wprost."""
    config = Config()
    config.shrink_per_wave = 1.0

    config.apply_upgrades(GameState(wave=5))

    assert config.ring_shrink_speed == 1.0 + 5 * 1.0


def test_shrink_ceiling_is_tunable():
    config = Config()
    config.max_shrink_speed = 10.0

    config.apply_upgrades(GameState(wave=100))

    assert config.ring_shrink_speed == 10.0


def test_spawn_interval_floor_is_tunable():
    config = Config()
    config.min_spawn_interval = 0.5

    config.apply_upgrades(GameState(wave=100))

    assert config.ring_spawn_interval == 0.5


def test_every_settings_slider_points_at_a_real_config_field():
    """Literówka w nazwie pola dałaby suwak, który cicho nic nie robi."""
    from ui.settings_view import _SLIDERS

    config = Config()
    missing = [field for _, field, *_ in _SLIDERS if not hasattr(config, field)]

    assert missing == []


def test_no_settings_slider_targets_a_derived_field():
    """Pola przeliczanego przez apply_upgrades nie da się ustawić suwakiem —
    wartość zniknie przy najbliższym zakupie albo awansie fali. Suwaki muszą
    celować w wejścia, nie w wyniki."""
    from ui.settings_view import _SLIDERS

    fresh = Config()
    recomputed = Config()
    recomputed.apply_upgrades(GameState(
        wave=3, upgrade_hole_size=1, upgrade_hole_count=1,
        upgrade_ball_size=1, upgrade_hole_speed=1, upgrade_ball_trail=1))

    derived = {name for name in vars(fresh)
               if getattr(fresh, name) != getattr(recomputed, name)}
    targeted = {field for _, field, *_ in _SLIDERS}

    assert targeted & derived == set()


def test_ball_damage_grows_exponentially_at_high_levels():
    """Dodawanie stałej przy koszcie wykładniczym daje wzrost logarytmiczny,
    a wymagania (HP okręgu) rosną liniowo z falą — dodawanie nigdy nie nadąży.
    Od poziomu ~12 prowadzenie przejmuje wykładnik."""
    config = Config()

    config.apply_upgrades(GameState(upgrade_ball_damage=20))

    assert config.ball_damage == round(1.25 ** 20)


def test_ball_damage_upgrade_has_no_dead_levels():
    """round(1.25^n) powtarzało wartość na poziomach 1, 3 i 4 — zakup za
    200 monet nie zmieniał wtedy nic, jak kiedyś rozmiar dziury bez dziury."""
    config = Config()

    damage = []
    for level in range(13):
        config.apply_upgrades(GameState(upgrade_ball_damage=level))
        damage.append(config.ball_damage)

    assert all(later > earlier for earlier, later in zip(damage, damage[1:]))


def test_ball_damage_is_at_least_one():
    config = Config()

    config.apply_upgrades(GameState())

    assert config.ball_damage == 1


def test_ball_damage_is_recomputed_not_accumulated():
    config = Config()
    state = GameState(upgrade_ball_damage=5)

    config.apply_upgrades(state)
    first = config.ball_damage
    config.apply_upgrades(state)

    assert config.ball_damage == first
