from formatting import short_number


def test_small_values_stay_plain():
    assert short_number(0) == "0"
    assert short_number(7) == "7"
    assert short_number(742) == "742"


def test_thousands_get_a_k():
    assert short_number(1_200) == "1.2K"
    assert short_number(12_300) == "12.3K"


def test_three_significant_digits_drop_the_decimal():
    """123.4K nie mieści się w pasku HUD, a dziesiąta część i tak nic nie wnosi
    przy tej skali."""
    assert short_number(123_400) == "123K"


def test_millions_and_billions_get_their_own_suffix():
    assert short_number(3_400_000) == "3.4M"
    assert short_number(1_500_000_000) == "1.5B"
    assert short_number(2_100_000_000_000) == "2.1T"


def test_beyond_the_suffix_table_falls_back_to_scientific():
    """Ujście dla monet jest nieograniczone, więc skala kiedyś wyjdzie
    poza tabelę przyrostków — nie może wtedy zwrócić bzdury."""
    assert short_number(5e18) == "5.00e+18"


def test_boundary_promotes_instead_of_printing_four_digits():
    """999.6 zaokrąglone do zera miejsc to '1000' — cztery cyfry tam, gdzie
    przyrostek istnieje właśnie po to, żeby ich uniknąć."""
    assert short_number(999.6) == "1.0K"
    assert short_number(999_600) == "1.0M"


def test_negative_values_keep_their_sign():
    assert short_number(-1_200) == "-1.2K"
