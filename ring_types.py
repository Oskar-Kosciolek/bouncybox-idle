import random
from dataclasses import dataclass

# Co ile fal pojawia się boss.
BOSS_EVERY: int = 10


@dataclass(frozen=True)
class RingType:
    """Wariant okręgu opisany liczbami, nie zachowaniem.

    Zamrożony, bo typ jest współdzielony przez wszystkie okręgi danego rodzaju —
    przypadkowa zmiana pola przestawiłaby balans dla całej planszy naraz.
    """

    id: str
    name: str                              # etykieta na planszy, pusta = bez etykiety
    color: tuple[int, int, int]
    hp_multiplier: float = 1.0             # względem state.get_ring_hp()
    shrink_multiplier: float = 1.0
    coin_multiplier: float = 1.0
    splits_into: int = 0                   # ile mniejszych okręgów po śmierci
    thickness: int = 4
    unlock_wave: int = 1
    weight: float = 0.0                    # waga losowania na fali odblokowania
    weight_per_wave: float = 0.0           # przyrost wagi za każdą kolejną falę

    def effective_weight(self, wave: int) -> float:
        """Waga losowania na danej fali — całą krzywą trudności robią te dwie liczby."""
        if wave < self.unlock_wave:
            return 0.0
        return max(0.0, self.weight + self.weight_per_wave * (wave - self.unlock_wave))


NORMAL = RingType(
    "normal", "", (60, 120, 200),
    unlock_wave=1, weight=10.0, weight_per_wave=-0.35,
)
FRAGILE = RingType(
    "fragile", "kruchy", (240, 200, 60),
    hp_multiplier=0.15, coin_multiplier=3.0,
    unlock_wave=2, weight=2.0,
)
ARMORED = RingType(
    "armored", "pancerny", (150, 155, 170),
    hp_multiplier=3.0, coin_multiplier=2.5, thickness=6,
    unlock_wave=4, weight=1.0, weight_per_wave=0.25,
)
SPLITTING = RingType(
    "splitting", "dzielacy sie", (170, 90, 200),
    hp_multiplier=0.6, coin_multiplier=0.6, splits_into=2,
    unlock_wave=6, weight=0.5, weight_per_wave=0.15,
)
BOSS = RingType(
    "boss", "BOSS", (220, 70, 70),
    hp_multiplier=4.0, shrink_multiplier=0.5, coin_multiplier=8.0, thickness=8,
    unlock_wave=BOSS_EVERY, weight=0.0,
)

RING_TYPES: list[RingType] = [NORMAL, FRAGILE, ARMORED, SPLITTING, BOSS]

# Boss stawiany jest deterministycznie co BOSS_EVERY fal, więc nie bierze
# udziału w losowaniu ważonym.
SPAWNABLE_TYPES: list[RingType] = [t for t in RING_TYPES if t is not BOSS]


def pick_type(wave: int, rng: random.Random) -> RingType:
    """Losuje typ okręgu ważony falą.

    `rng` jest wstrzykiwany, bo rozkład typów to jedyna część systemu, w której
    błąd strojenia jest niewidoczny gołym okiem — z ustalonym ziarnem da się go
    sprawdzić testem.
    """
    weights = [t.effective_weight(wave) for t in SPAWNABLE_TYPES]
    if sum(weights) <= 0.0:
        return NORMAL
    return rng.choices(SPAWNABLE_TYPES, weights=weights, k=1)[0]
