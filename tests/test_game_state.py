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


HOUR = 3600.0


def test_no_offline_earnings_without_a_previous_session():
    """Świeży stan ma last_played_at = 0.0, czyli epokę Uniksa. Bez tej bramki
    nowy gracz dostałby pełny limit naliczenia na starcie."""
    state = GameState(wave=10, last_played_at=0.0)

    away, coins = state.offline_earnings(now=1_000_000.0)

    assert (away, coins) == (0.0, 0.0)


def test_offline_earnings_scale_with_the_wave():
    early = GameState(wave=5, last_played_at=0.0)
    late = GameState(wave=40, last_played_at=0.0)
    early.last_played_at = late.last_played_at = 1000.0

    _, early_coins = early.offline_earnings(now=1000.0 + HOUR)
    _, late_coins = late.offline_earnings(now=1000.0 + HOUR)

    assert late_coins > early_coins


def test_auto_collector_doubles_the_offline_rate():
    plain = GameState(wave=10, last_played_at=1000.0)
    upgraded = GameState(wave=10, last_played_at=1000.0,
                         upgrade_auto_collector=1)

    _, plain_coins = plain.offline_earnings(now=1000.0 + HOUR)
    _, upgraded_coins = upgraded.offline_earnings(now=1000.0 + HOUR)

    assert upgraded_coins == plain_coins * 2


def test_offline_earnings_are_capped():
    """Bez limitu tygodniowa przerwa dawałaby tyle, ile miesiąc grania."""
    state = GameState(wave=10, last_played_at=1000.0)

    away_a_day, coins_a_day = state.offline_earnings(now=1000.0 + 24 * HOUR)
    away_a_week, coins_a_week = state.offline_earnings(now=1000.0 + 168 * HOUR)

    assert coins_a_day == coins_a_week
    assert away_a_day == away_a_week


def test_clock_going_backwards_earns_nothing():
    """Zmiana strefy albo korekta zegara nie może być źródłem monet."""
    state = GameState(wave=10, last_played_at=5000.0)

    away, coins = state.offline_earnings(now=1000.0)

    assert (away, coins) == (0.0, 0.0)


def test_claiming_offline_adds_the_coins():
    state = GameState(wave=10, last_played_at=1000.0)

    _, coins = state.claim_offline(now=1000.0 + HOUR)

    assert coins > 0
    assert state.coins > 0


def test_offline_cannot_be_claimed_twice():
    """Naliczenie przesuwa znacznik, więc powtórne wywołanie nie płaci."""
    state = GameState(wave=10, last_played_at=1000.0)

    state.claim_offline(now=1000.0 + HOUR)
    _, second = state.claim_offline(now=1000.0 + HOUR)

    assert second == 0.0


def test_ring_hp_grows_exponentially_with_the_wave():
    """HP rosło liniowo (8x przez sesję), a obrażenia wykładniczo (87x), więc
    cios dziury przerastał każdy okrąg i typy przestawały się różnić."""
    ratios = [GameState(wave=w + 1).get_ring_hp() / GameState(wave=w).get_ring_hp()
              for w in (5, 20, 50)]

    assert all(abs(r - ratios[0]) < 0.01 for r in ratios)
    assert ratios[0] > 1.05


def test_ring_hp_is_unchanged_on_the_first_wave():
    assert GameState(wave=1).get_ring_hp() == 100


def test_payout_grows_at_the_same_rate_as_ring_hp():
    """Różne tempa rozjechałyby ekonomię: twardsze okręgi za tę samą stawkę
    znaczą, że każda kolejna fala opłaca się mniej."""
    hp_ratio = GameState(wave=21).get_ring_hp() / GameState(wave=20).get_ring_hp()
    pay_ratio = GameState(wave=21).ring_payout() / GameState(wave=20).ring_payout()

    assert abs(hp_ratio - pay_ratio) < 0.01


def test_destroying_a_ring_pays_the_wave_payout():
    """Jedna formuła wypłaty dla zniszczenia i dla offline — dwie niezależne
    właśnie dlatego się rozjechały."""
    state = GameState(wave=12)

    coins = state.on_ring_destroyed()

    assert coins == state.ring_payout()


def test_offline_rate_follows_the_payout_curve():
    """Stawka liniowa przy wykładniczych monetach dawała 274% zarobku
    aktywnego na fali 10 i 3,7% na fali 70."""
    low = GameState(wave=10, last_played_at=1000.0)
    high = GameState(wave=40, last_played_at=1000.0)

    _, low_coins = low.offline_earnings(now=1000.0 + HOUR)
    _, high_coins = high.offline_earnings(now=1000.0 + HOUR)

    assert abs(high_coins / low_coins
               - high.ring_payout() / low.ring_payout()) < 0.01


def test_offline_never_pays_more_than_destroying_rings_by_hand():
    """Stawka offline to ułamek okręgu na sekundę — musi zostać ułamkiem."""
    from game_state import OFFLINE_RINGS_PER_SECOND

    assert 0.0 < OFFLINE_RINGS_PER_SECOND < 0.3
