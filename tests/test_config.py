from config import Config
from game_state import GameState


def test_apply_upgrades_dwa_razy_daje_ten_sam_wynik():
    """apply_upgrades jest wołane przy każdym zakupie, awansie fali i prestige.
    Musi przeliczać wartości od zera, a nie doklejać ich do poprzednich."""
    config = Config()
    state = GameState()
    state.upgrade_hole_size = 3

    config.apply_upgrades(state)
    po_pierwszym = config.hole_size

    config.apply_upgrades(state)

    assert config.hole_size == po_pierwszym


def test_dziura_nie_przekracza_pelnego_okregu_przy_maksymalnych_ulepszeniach():
    """Dziura 360° oznaczałaby okrąg złożony wyłącznie z dziury — piłka
    niszczyłaby go pierwszym dotknięciem. Max: 5x10° + 5x8° prestige = 90°."""
    config = Config()
    state = GameState()
    state.upgrade_hole_size = 5
    state.prestige_hole_size = 5

    for _ in range(20):          # 20 zakupów/awansów fali
        config.apply_upgrades(state)

    assert config.hole_size == 90.0


def test_predkosc_zwezania_zalezy_tylko_od_biezacej_fali():
    """Gracz przechodzący fale 1..10 musi mieć tę samą trudność co gracz,
    który wczytał zapis z falą 10."""
    przechodzacy = Config()
    state = GameState()
    for fala in range(1, 11):
        state.wave = fala
        przechodzacy.apply_upgrades(state)

    wczytany = Config()
    wczytany.apply_upgrades(GameState(wave=10))

    assert przechodzacy.ring_shrink_speed == wczytany.ring_shrink_speed


def test_rozmiar_pilki_rosnie_o_2px_na_poziom():
    config = Config()
    state = GameState(upgrade_ball_size=3)

    config.apply_upgrades(state)
    config.apply_upgrades(state)

    assert config.ball_radius == 5 + 3 * 2


def test_liczba_dziur_nie_kumuluje_sie_miedzy_wywolaniami():
    config = Config()
    state = GameState(upgrade_hole_count=2)

    for _ in range(5):
        config.apply_upgrades(state)

    assert config.hole_count == 2
