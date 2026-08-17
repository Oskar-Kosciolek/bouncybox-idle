import os
import random

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from audio import ring_tension  # noqa: E402
from music import (  # noqa: E402
    BEAT_FAST,
    BEAT_SLOW,
    NOTE_COUNT,
    Music,
    beat_interval,
    next_degree,
)


def test_ring_tension_peaks_when_the_ring_reaches_minimum():
    assert ring_tension(30.0, min_radius=30.0, start_radius=220.0) == 1.0
    assert ring_tension(220.0, min_radius=30.0, start_radius=220.0) == 0.0


def test_higher_waves_play_faster():
    assert beat_interval(wave=40) < beat_interval(wave=1)


def test_tension_speeds_the_pulse_up():
    assert beat_interval(wave=5, tension=1.0) < beat_interval(wave=5, tension=0.0)


def test_beat_interval_stays_between_its_bounds():
    """Bez podłogi wysokie fale zamieniłyby melodię w terkot."""
    fastest = beat_interval(wave=10_000, tension=1.0)
    slowest = beat_interval(wave=1, tension=0.0)

    assert fastest == BEAT_FAST
    assert slowest <= BEAT_SLOW


def test_melody_stays_within_the_scale():
    rng = random.Random(5)
    degree = 0

    for _ in range(2000):
        degree = next_degree(degree, rng)
        assert 0 <= degree < NOTE_COUNT


def test_melody_moves_in_small_steps():
    """Losowanie z kapelusza brzmi jak piknięcia. Błądzenie małymi krokami
    brzmi jak linia melodyczna."""
    rng = random.Random(5)
    degree = NOTE_COUNT // 2

    for _ in range(500):
        nxt = next_degree(degree, rng)
        assert abs(nxt - degree) <= 2
        degree = nxt


def test_tension_biases_the_melody_upward():
    """Zaciskający się okrąg ma pchać melodię w górę — to ta sama informacja
    co rosnąca wysokość odbić, tylko w dłuższej skali czasu."""
    def drift(bias: float) -> float:
        total = 0
        for seed in range(40):
            rng = random.Random(seed)
            degree = NOTE_COUNT // 2
            for _ in range(20):
                degree = next_degree(degree, rng, upward_bias=bias)
            total += degree
        return total / 40

    assert drift(1.0) > drift(0.0)


def test_music_degrades_to_silence_without_a_mixer(monkeypatch):
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)

    music = Music()

    assert music.available is False
    music.update(dt=1.0, wave=5, tension=0.5)


def test_zero_volume_plays_nothing():
    music = Music(volume=0.0)

    music.update(dt=10.0, wave=5, tension=0.5)

    assert music.volume == 0.0


def test_melody_does_not_settle_on_the_edges_of_the_scale():
    """Błądzenie losowe po ograniczonym zakresie osiada na brzegach — bez siły
    przywracającej wychodziło pięć nut pod rząd na najniższym stopniu."""
    stuck = 0
    total = 0
    for seed in range(20):
        rng = random.Random(seed)
        degree = 0
        for _ in range(200):
            degree = next_degree(degree, rng)
            stuck += degree in (0, NOTE_COUNT - 1)
            total += 1

    assert stuck < total * 0.12
