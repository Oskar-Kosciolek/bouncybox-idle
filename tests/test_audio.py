import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")   # testy nie zależą od karty

import pygame  # noqa: E402

from audio import (  # noqa: E402
    BOUNCE_MIN_INTERVAL,
    SAMPLE_RATE,
    Audio,
    bounce_frequency,
    should_play_bounce,
    tone_bytes,
)


def test_shrinking_ring_sounds_higher():
    """Narastające zagrożenie ma być słyszalne, zanim stanie się widoczne."""
    wide = bounce_frequency(220.0, min_radius=30.0, start_radius=220.0)
    tight = bounce_frequency(40.0, min_radius=30.0, start_radius=220.0)

    assert tight > wide


def test_frequency_stays_in_range_outside_the_expected_radii():
    """Promień bywa poza zakresem: dzieci po podziale i okręgi dociśnięte
    do minimum wychodzą poza założone widełki."""
    below = bounce_frequency(5.0, min_radius=30.0, start_radius=220.0)
    above = bounce_frequency(500.0, min_radius=30.0, start_radius=220.0)

    assert below == bounce_frequency(30.0, min_radius=30.0, start_radius=220.0)
    assert above == bounce_frequency(220.0, min_radius=30.0, start_radius=220.0)


def test_bounce_is_throttled():
    """Kilka piłek po 5 odbić na sekundę to ~15 dźwięków — bez dławienia
    zlewa się to w terkot i wyczerpuje kanały miksera."""
    assert should_play_bounce(last_play=10.0, now=10.0 + BOUNCE_MIN_INTERVAL)
    assert not should_play_bounce(last_play=10.0,
                                  now=10.0 + BOUNCE_MIN_INTERVAL / 2)


def test_tone_length_matches_the_sample_rate():
    data = tone_bytes(440.0, 0.1, channels=1)

    assert len(data) == int(SAMPLE_RATE * 0.1) * 2   # 16 bitów = 2 bajty


def test_tone_is_interleaved_for_every_channel():
    """Mikser wymusza stereo nawet gdy prosić o mono. Bufor mono odtworzony
    jako stereo gra o połowę za krótko — cichy błąd, nie wyjątek."""
    mono = tone_bytes(440.0, 0.1, channels=1)
    stereo = tone_bytes(440.0, 0.1, channels=2)

    assert len(stereo) == 2 * len(mono)


def test_audio_degrades_to_silence_without_a_device(monkeypatch):
    """Brak karty dźwiękowej nie może wywalić gry."""
    def no_device(**kwargs):
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "init", no_device)

    audio = Audio()

    assert audio.available is False
    audio.bounce(radius=100.0, min_radius=30.0, start_radius=220.0, now=0.0)
    audio.ring_destroyed()
    audio.crush()
    audio.purchase()


def test_zero_volume_is_silent_but_still_available():
    """Wyciszenie to suwak na zero, nie brak miksera — gra działa dalej."""
    audio = Audio(volume=0.0)

    audio.bounce(radius=100.0, min_radius=30.0, start_radius=220.0, now=0.0)
    audio.ring_destroyed()

    assert audio.volume == 0.0
