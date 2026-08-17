"""Generatywna warstwa muzyczna — sekwencer, nie nagranie.

Gra bywa zostawiana w tle na godziny, a krótka pętla po czterdziestym
powtórzeniu staje się powodem, żeby wyciszyć dźwięk. Dlatego melodia nie jest
zapisana, tylko układana na bieżąco: błądzenie po skali pentatonicznej z
pauzami, którego tempo i kierunek idą za stanem gry. Nie ma czego zapamiętać,
więc nie ma się czym znudzić.
"""

import random

import pygame

from audio import tone_bytes

# Pentatonika molowa — w niej trudno zagrać fałsz, więc losowanie nie
# wyprodukuje kakofonii.
SCALE_SEMITONES: tuple[int, ...] = (0, 3, 5, 7, 10)
OCTAVES: int = 3
NOTE_COUNT: int = len(SCALE_SEMITONES) * OCTAVES
ROOT_HZ: float = 220.0

NOTE_SECONDS: float = 0.9      # długie wybrzmienie: nuty zachodzą jak pad
NOTE_DECAY: float = 3.5

BEAT_SLOW: float = 0.55        # odstęp między nutami na starcie
BEAT_FAST: float = 0.30        # podłoga — bez niej wysokie fale terkoczą
REST_CHANCE: float = 0.25      # pauzy dają oddech

_STEPS: tuple[int, ...] = (-2, -1, 0, 1, 2)
_STEP_WEIGHTS: tuple[float, ...] = (1.0, 3.0, 1.5, 3.0, 1.0)

# Siła ciągnąca melodię ku środkowi skali. Bez niej błądzenie losowe po
# ograniczonym zakresie osiada na brzegach — wychodziło pięć nut pod rząd
# na najniższym stopniu.
_CENTRE_PULL: float = 0.6


def beat_interval(wave: int, tension: float = 0.0) -> float:
    """Ile sekund między nutami — szybciej z falą i z napięciem."""
    tension = max(0.0, min(1.0, tension))
    interval = BEAT_SLOW - wave * 0.005 - tension * 0.12
    return max(BEAT_FAST, min(BEAT_SLOW, interval))


def next_degree(current: int, rng: random.Random,
                upward_bias: float = 0.0) -> int:
    """Kolejny stopień skali — błądzenie losowe małymi krokami.

    Losowanie z całej skali brzmi jak przypadkowe piknięcia; ruch o jeden-dwa
    stopnie brzmi jak linia melodyczna. `upward_bias` przechyla wybór w górę,
    dzięki czemu zaciskający się okrąg pcha melodię w wyższy rejestr.
    """
    centre = (NOTE_COUNT - 1) / 2.0
    pull = (centre - current) / centre        # +1 na samym dole, -1 na górze
    drift = max(0.0, min(1.0, upward_bias)) + _CENTRE_PULL * pull
    drift = max(-1.0, min(1.0, drift))

    weights = [
        max(0.05, weight * (1.0 + drift * (0.8 if step > 0
                                           else -0.8 if step < 0 else 0.0)))
        for weight, step in zip(_STEP_WEIGHTS, _STEPS)
    ]
    step = rng.choices(_STEPS, weights=weights, k=1)[0]
    return max(0, min(NOTE_COUNT - 1, current + step))


class Music:
    """Sekwencer grający nuty w takt stanu gry.

    Wymaga miksera zainicjowanego wcześniej przez `Audio` — bez niego
    staje się atrapą, tak jak reszta warstwy dźwiękowej.
    """

    def __init__(self, volume: float = 0.25,
                 rng: random.Random | None = None) -> None:
        self.volume = volume
        self.available = False
        self._notes: list[pygame.mixer.Sound] = []
        self._degree = NOTE_COUNT // 2
        self._timer = 0.0
        self._rng = rng if rng is not None else random.Random()

        if not pygame.mixer.get_init():
            return

        self.available = True
        self._build()

    def _build(self) -> None:
        """Generuje wszystkie nuty raz, przy starcie (~190 ms)."""
        channels = pygame.mixer.get_init()[2]
        self._notes = []
        for octave in range(OCTAVES):
            for semitone in SCALE_SEMITONES:
                freq = ROOT_HZ * 2.0 ** ((semitone + 12 * octave) / 12.0)
                self._notes.append(pygame.mixer.Sound(
                    buffer=tone_bytes(freq, NOTE_SECONDS, channels=channels,
                                      decay=NOTE_DECAY,
                                      harmonics=((1.0, 1.0), (2.0, 0.25)))))

    def update(self, dt: float, wave: int, tension: float) -> None:
        """Woła się co klatkę; gra nutę, gdy minie odstęp."""
        if not self.available or self.volume <= 0.0:
            return

        self._timer -= dt
        if self._timer > 0.0:
            return

        self._timer = beat_interval(wave, tension)
        self._degree = next_degree(self._degree, self._rng,
                                   upward_bias=tension)

        if self._rng.random() < REST_CHANCE:
            return

        note = self._notes[self._degree]
        note.set_volume(self.volume)
        note.play()
