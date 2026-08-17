"""Generatywna warstwa muzyczna — sekwencer, nie nagranie.

Gra bywa zostawiana w tle na godziny, a krótka pętla po czterdziestym
powtórzeniu staje się powodem, żeby wyciszyć dźwięk. Dlatego melodia nie jest
zapisana, tylko układana na bieżąco: błądzenie po skali pentatonicznej z
pauzami, którego tempo i kierunek idą za stanem gry. Nie ma czego zapamiętać,
więc nie ma się czym znudzić.
"""

import array
import math
import random

import pygame

from audio import SAMPLE_RATE

# Barwy nut. Każda składowa to (mnożnik częstotliwości, amplituda, tempo
# gaśnięcia). Osobne tempo na składową jest tym, co odróżnia instrument od
# piszczyka: w rzeczywistych instrumentach wyższe harmoniczne gasną szybciej,
# a gdy gasną równo, brzmi to jak organy elektroniczne.
TIMBRES: dict[str, dict] = {
    # Kalimba / pozytywka — czysty atak, szybko gasnące wyższe składowe
    "kalimba": {
        "attack": 0.006,
        "partials": ((1.0, 1.0, 3.0), (2.0, 0.5, 6.0),
                     (3.0, 0.22, 9.0), (4.2, 0.10, 12.0)),
    },
    # Marimba / drewno — krótkie, matowe, mocna czwarta harmoniczna
    "marimba": {
        "attack": 0.003,
        "partials": ((1.0, 1.0, 5.0), (4.0, 0.40, 14.0), (10.0, 0.08, 22.0)),
    },
    # Miękki dzwonek — długi ogon, lekko nieharmoniczne składowe
    "dzwonek": {
        "attack": 0.010,
        "partials": ((1.0, 1.0, 2.0), (2.0, 0.30, 4.0),
                     (2.76, 0.20, 5.5), (5.4, 0.06, 9.0)),
    },
    # Fortepian — miękkie uderzenie młoteczka i długo trzymająca podstawowa,
    # nad którą górne składowe gasną kilka razy szybciej, więc barwa z czasem
    # się ociepla. Mnożniki wyższych składowych są lekko podwyższone: struna
    # ma sztywność, przez co jej alikwoty leżą nieco powyżej wielokrotności
    # podstawowej. To ta rozstrojka odróżnia fortepian od piszczyka.
    "pianino": {
        "attack": 0.008,
        "partials": ((1.00, 1.00, 1.3), (2.00, 0.55, 2.2),
                     (3.01, 0.30, 3.2), (4.03, 0.16, 4.4),
                     (5.06, 0.08, 6.0)),
    },
}


# Tablica sinusa. Naiwna pętla wołała `sin` i `exp` po dwa miliony razy na
# komplet nut, co dawało 876 ms zawieszenia przy starcie gry. Odczyt z tablicy
# i przyrostowe gaśnięcie zamieniają to na mnożenia.
_SINE_BITS: int = 11
_SINE_SIZE: int = 1 << _SINE_BITS
_SINE_MASK: int = _SINE_SIZE - 1
_SINE: tuple[float, ...] = tuple(
    math.sin(2.0 * math.pi * i / _SINE_SIZE) for i in range(_SINE_SIZE))


def note_bytes(freq: float, seconds: float, channels: int = 2,
               timbre: str = "kalimba") -> bytes:
    """Nuta z narastaniem i osobnym gaśnięciem każdej składowej.

    Osobny generator od `tone_bytes`, bo efekty i nuty mają inne wymagania:
    efekt ma uderzyć od razu, nuta ma być szarpnięta. Bez rampy narastania
    początek nuty jest skokiem amplitudy, co ucho słyszy jako pstryknięcie —
    i to właśnie ono robi z instrumentu piszczyk.
    """
    spec = TIMBRES[timbre]
    attack = spec["attack"]
    partials = spec["partials"]

    frames = int(SAMPLE_RATE * seconds)
    total_amp = sum(amp for _, amp, _ in partials) or 1.0

    # Jeden przebieg na składową, wszystko na zmiennych lokalnych. Wersja
    # przeplatająca składowe w jednej pętli indeksowała listy przy każdej
    # próbce, co w Pythonie kosztuje więcej niż samo liczenie dźwięku.
    acc = [0.0] * frames
    sine, size, mask = _SINE, _SINE_SIZE, _SINE_MASK

    for mult, amp, decay in partials:
        # Każda składowa liczona tylko dopóki ją słychać. Górne gasną kilka
        # razy szybciej niż podstawowa — piąta składowa fortepianu cichnie po
        # 0,58 s, a nuta trwa 2,70 s, więc liczenie jej do końca to w czterech
        # piątych generowanie zera.
        span = min(frames, int(SAMPLE_RATE * _audible_seconds(decay)) + 1)
        phase = 0.0
        phase_step = freq * mult / SAMPLE_RATE
        env = amp / total_amp
        env_step = math.exp(-decay / SAMPLE_RATE)
        for i in range(span):
            acc[i] += env * sine[int(phase * size) & mask]
            phase += phase_step
            env *= env_step

    attack_frames = max(1, int(attack * SAMPLE_RATE))
    mono = array.array("h", bytes(frames * 2))

    for i in range(frames):
        value = acc[i]
        if i < attack_frames:
            value *= i / attack_frames
        mono[i] = int(max(-1.0, min(1.0, value)) * 32000)

    if channels == 1:
        return mono.tobytes()

    # Przeplatanie wycinkiem zamiast próbka po próbce
    out = array.array("h", bytes(frames * channels * 2))
    for channel in range(channels):
        out[channel::channels] = mono
    return out.tobytes()

# Pentatonika molowa — w niej trudno zagrać fałsz, więc losowanie nie
# wyprodukuje kakofonii.
SCALE_SEMITONES: tuple[int, ...] = (0, 3, 5, 7, 10)
OCTAVES: int = 3
NOTE_COUNT: int = len(SCALE_SEMITONES) * OCTAVES
ROOT_HZ: float = 220.0

NOTE_TIMBRE: str = "dzwonek"

# Poniżej tego ułamka szczytu nuty już nie słychać — dalsze próbki to
# generowanie ciszy. Przy sztywnych 1,6 s ostatnie pół sekundy kalimby
# schodziło do 4% amplitudy i kosztowało jedną trzecią czasu startu.
NOTE_SILENCE_THRESHOLD: float = 0.03


def _audible_seconds(decay: float) -> float:
    """Jak długo składowa o danym tempie gaśnięcia jest jeszcze słyszalna."""
    return -math.log(NOTE_SILENCE_THRESHOLD) / decay


def note_seconds(timbre: str) -> float:
    """Ile nuta wybrzmiewa, zanim ucichnie poniżej progu słyszalności.

    Decyduje najwolniej gasnąca składowa — to ona zostaje na końcu.
    """
    slowest = min(decay for _, _, decay in TIMBRES[timbre]["partials"])
    return _audible_seconds(slowest)

# Puls szybszy niż wybrzmienie nuty, więc nuty zachodzą na siebie i zamiast
# pojedynczych uderzeń powstaje ciągła tkanka. To dlatego "szybciej" daje tu
# spokojniejsze brzmienie, a nie bardziej urywane.
BEAT_SLOW: float = 0.42        # odstęp między nutami na starcie
BEAT_FAST: float = 0.24        # podłoga — bez niej wysokie fale terkoczą
REST_CHANCE: float = 0.12      # rzadkie pauzy: przerwa ma być oddechem,
                               # nie dziurą rwącą linię

# Krok o jeden stopień dominuje — duże skoki brzmią nerwowo.
_STEPS: tuple[int, ...] = (-2, -1, 0, 1, 2)
_STEP_WEIGHTS: tuple[float, ...] = (0.5, 4.0, 1.2, 4.0, 0.5)

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
                 rng: random.Random | None = None,
                 timbre: str = NOTE_TIMBRE) -> None:
        self.volume = volume
        self.timbre = timbre
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
        seconds = note_seconds(self.timbre)
        self._notes = []
        for octave in range(OCTAVES):
            for semitone in SCALE_SEMITONES:
                freq = ROOT_HZ * 2.0 ** ((semitone + 12 * octave) / 12.0)
                self._notes.append(pygame.mixer.Sound(
                    buffer=note_bytes(freq, seconds, channels=channels,
                                      timbre=self.timbre)))

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
