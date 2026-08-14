from timestep import FixedTimestep


def test_symulacja_nadaza_za_zegarem_przy_60_fps():
    """10 sekund realnych = 10 sekund symulacji. Poprzedni `min(dt, 0.01)`
    przy 60 FPS ścinał każdą klatkę do 0.01 s i dawał 6 s zamiast 10."""
    zegar = FixedTimestep()
    klatka = 1 / 60

    kroki = sum(zegar.steps(klatka) for _ in range(600))
    czas_symulacji = kroki * zegar.step

    assert abs(czas_symulacji - 10.0) < zegar.step


def test_reszta_kroku_przenosi_sie_na_nastepna_klatke():
    """Klatka krótsza od kroku fizyki nie znika — kumuluje się."""
    zegar = FixedTimestep()
    polowa_kroku = zegar.step / 2

    assert zegar.steps(polowa_kroku) == 0
    assert zegar.steps(polowa_kroku) == 1


def test_dlugie_zaciecie_nie_powoduje_spirali_smierci():
    """Po 2-sekundowej zwiesze (np. przeciąganie okna) nie nadrabiamy
    480 kroków w jednej klatce — to zawiesiłoby grę na dobre."""
    zegar = FixedTimestep()

    kroki = zegar.steps(2.0)

    assert 0 < kroki <= zegar.max_steps


def test_po_zacieciu_zaleglosc_nie_wraca_w_kolejnych_klatkach():
    """Porzucona zaległość musi zniknąć, inaczej gra nadrabia ją w nieskończoność."""
    zegar = FixedTimestep()
    zegar.steps(2.0)

    kroki = zegar.steps(1 / 60)

    assert 0 < kroki <= zegar.max_steps
