"""Dźwięk generowany proceduralnie — bez plików i bez dodatkowych zależności.

`numpy` nie jest zainstalowany, więc `pygame.sndarray` odpada. Tony powstają
jako surowy bufor 16-bitowych próbek i trafiają wprost do `pygame.mixer.Sound`.
Wszystko generuje się raz przy starcie: 22 tysiące sinusów na klatkę byłoby
za drogie, a odbicia zdarzają się kilkanaście razy na sekundę.
"""

import array
import math

import pygame

SAMPLE_RATE: int = 22050

# Dławienie odbić. Przy kilku piłkach po ~5 odbić na sekundę bez limitu
# powstaje terkot, a domyślna pula kanałów miksera wyczerpuje się i pygame
# zaczyna ucinać dźwięki w losowych momentach.
BOUNCE_MIN_INTERVAL: float = 0.06

# Widełki wysokości odbicia: szeroki okrąg brzmi nisko, dociśnięty wysoko.
BOUNCE_LOW_HZ: float = 300.0
BOUNCE_HIGH_HZ: float = 900.0
BOUNCE_PITCH_STEPS: int = 12

_MIXER_CHANNELS: int = 24


def ring_tension(radius: float, min_radius: float,
                 start_radius: float) -> float:
    """Jak blisko zduszenia jest okrąg: 1.0 na minimum, 0.0 świeżo postawiony.

    Promień bywa poza widełkami — dzieci po podziale i okręgi dociśnięte do
    minimum — więc wynik jest przycinany.
    """
    span = max(1.0, start_radius - min_radius)
    ratio = (radius - min_radius) / span
    return max(0.0, min(1.0, 1.0 - ratio))


def bounce_frequency(radius: float, min_radius: float,
                     start_radius: float) -> float:
    """Wysokość odbicia dla okręgu o danym promieniu.

    Kurczący się okrąg brzmi coraz wyżej, więc narastające zagrożenie słychać,
    zanim się je zobaczy.
    """
    tension = ring_tension(radius, min_radius, start_radius)
    return BOUNCE_LOW_HZ + (BOUNCE_HIGH_HZ - BOUNCE_LOW_HZ) * tension


def should_play_bounce(last_play: float, now: float) -> bool:
    """Czy minęło dość czasu od poprzedniego odbicia, żeby zagrać kolejne."""
    return now - last_play >= BOUNCE_MIN_INTERVAL


def tone_bytes(freq: float, seconds: float, channels: int = 2,
               decay: float = 5.0,
               harmonics: tuple[tuple[float, float], ...] = ((1.0, 1.0),),
               ) -> bytes:
    """Ton z wykładniczo opadającą kopertą, przeplatany na wszystkie kanały.

    Koperta robi z tego uderzenie zamiast pisku. Przeplatanie jest konieczne,
    bo mikser wymusza stereo nawet gdy prosić o mono, a bufor mono odtworzony
    jako stereo gra o połowę za krótko — cichy błąd, nie wyjątek.
    """
    frames = int(SAMPLE_RATE * seconds)
    data = array.array("h")
    total_amp = sum(amp for _, amp in harmonics) or 1.0

    for i in range(frames):
        t = i / SAMPLE_RATE
        envelope = math.exp(-decay * t / max(seconds, 1e-6))
        value = sum(amp * math.sin(2.0 * math.pi * freq * mult * t)
                    for mult, amp in harmonics) / total_amp
        sample = int(max(-1.0, min(1.0, value * envelope)) * 32000)
        for _ in range(channels):
            data.append(sample)

    return data.tobytes()


class Audio:
    """Biblioteka dźwięków gry. Bez urządzenia audio staje się atrapą."""

    def __init__(self, volume: float = 0.4) -> None:
        self.volume = volume
        self.available = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._bounce_tones: list[pygame.mixer.Sound] = []
        self._last_bounce: float = float("-inf")

        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16,
                              channels=2, buffer=512)
            pygame.mixer.set_num_channels(_MIXER_CHANNELS)
        except pygame.error:
            return   # gra działa dalej, po prostu w ciszy

        self.available = True
        self._build()

    # ------------------------------------------------------------------
    # Budowa biblioteki
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Generuje wszystkie dźwięki raz, przy starcie."""
        channels = pygame.mixer.get_init()[2]

        def sound(**kwargs) -> pygame.mixer.Sound:
            return pygame.mixer.Sound(
                buffer=tone_bytes(channels=channels, **kwargs))

        # Odbicia: kilkanaście gotowych wysokości, bez generowania w locie
        step = (BOUNCE_HIGH_HZ - BOUNCE_LOW_HZ) / (BOUNCE_PITCH_STEPS - 1)
        self._bounce_tones = [
            sound(freq=BOUNCE_LOW_HZ + step * i, seconds=0.05, decay=9.0)
            for i in range(BOUNCE_PITCH_STEPS)
        ]

        self._sounds = {
            # Trafienie w dziurę — niższe i pełniejsze niż odbicie
            "hole": sound(freq=220.0, seconds=0.12, decay=6.0,
                          harmonics=((1.0, 1.0), (2.0, 0.4))),
            # Zniszczenie okręgu — akord w górę, moment nagrody
            "destroy": sound(freq=440.0, seconds=0.22, decay=5.0,
                             harmonics=((1.0, 1.0), (1.5, 0.6), (2.0, 0.35))),
            # Zduszenie — niski, rozstrojony dudnienie, moment kary
            "crush": sound(freq=90.0, seconds=0.5, decay=3.0,
                           harmonics=((1.0, 1.0), (1.06, 0.8))),
            "powerup": sound(freq=660.0, seconds=0.18, decay=4.0,
                             harmonics=((1.0, 1.0), (2.0, 0.5), (3.0, 0.25))),
            "purchase": sound(freq=520.0, seconds=0.08, decay=8.0),
            "achievement": sound(freq=523.0, seconds=0.35, decay=3.0,
                                 harmonics=((1.0, 1.0), (1.26, 0.7),
                                            (1.5, 0.7))),
        }

    # ------------------------------------------------------------------
    # Odtwarzanie
    # ------------------------------------------------------------------

    def _play(self, name: str, gain: float = 1.0) -> None:
        """Odtwarza dźwięk po nazwie.

        Sprawdzenie dostępności musi wyprzedzać odczyt ze słownika — bez
        miksera słownik jest pusty i sam odczyt rzuciłby KeyError.
        """
        if not self.available or self.volume <= 0.0:
            return
        sound = self._sounds[name]
        sound.set_volume(self.volume * gain)
        sound.play()

    def bounce(self, radius: float, min_radius: float,
               start_radius: float, now: float) -> None:
        """Odbicie od okręgu — wysokość rośnie, gdy okrąg się kurczy."""
        if not self.available or self.volume <= 0.0:
            return
        if not should_play_bounce(self._last_bounce, now):
            return
        self._last_bounce = now

        freq = bounce_frequency(radius, min_radius, start_radius)
        span = BOUNCE_HIGH_HZ - BOUNCE_LOW_HZ
        index = round((freq - BOUNCE_LOW_HZ) / span * (BOUNCE_PITCH_STEPS - 1))
        index = max(0, min(BOUNCE_PITCH_STEPS - 1, index))
        sound = self._bounce_tones[index]
        sound.set_volume(self.volume * 0.35)
        sound.play()

    def hole_hit(self) -> None:
        self._play("hole", gain=0.7)

    def ring_destroyed(self) -> None:
        self._play("destroy")

    def crush(self) -> None:
        self._play("crush")

    def powerup(self) -> None:
        self._play("powerup", gain=0.8)

    def purchase(self) -> None:
        self._play("purchase", gain=0.6)

    def achievement(self) -> None:
        self._play("achievement")
