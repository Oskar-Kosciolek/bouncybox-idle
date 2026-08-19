from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState


# Zmierzony przychód na minutę w momencie, w którym gracz faktycznie kupuje
# daną warstwę: warstwę 1 podczas bootstrapu, warstwę 2 koło fali 10,
# warstwę 3 koło fali 25. Kotwica jest przychodem, nie wypłatą za okrąg —
# od fali 10 gracz zbiera ~430 okręgów na minutę i ta liczba się wypłaszcza,
# ale między falą 1 a 10 podwaja się, więc sama wypłata zaniżyłaby warstwę 1
# dwukrotnie względem reszty drzewka.
INCOME_AT_UNLOCK: dict[int, float] = {1: 150.0, 10: 15_000.0, 25: 90_000.0}


def _validate_unlock_waves(upgrades: list["Upgrade"]) -> None:
    """Sprawdza, że każda warstwa ma kotwicę kosztu.

    Wołane przy imporcie modułu, nie przy pierwszym zakupie — ulepszenie
    z nieznaną falą odblokowania rzuciłoby KeyError dopiero wtedy, gdy gracz
    kliknie węzeł, czyli po godzinie gry.
    """
    for upg in upgrades:
        if upg.unlock_wave not in INCOME_AT_UNLOCK:
            raise ValueError(
                f"{upg.id}: unlock_wave={upg.unlock_wave} nie ma kotwicy "
                f"w INCOME_AT_UNLOCK (dozwolone: {sorted(INCOME_AT_UNLOCK)})")


@dataclass
class Upgrade:
    id: str
    name: str
    description: str
    branch: str           # "ball" | "rings" | "economy"
    max_level: Optional[int]   # None = bez sufitu poziomów
    cost_minutes: float   # ile minut gry ma kosztować pierwszy poziom
    cost_multiplier: float = 2.0  # każdy poziom droższy x razy
    requires: Optional[str] = None   # id innego upgrade który musi być > 0
    unlock_wave: int = 1   # warstwa: 1, 10 albo 25

    @property
    def base_cost(self) -> float:
        """Koszt pierwszego poziomu w monetach.

        Liczony, nie wpisany: stała w kodzie nie wie nic o ekonomii, która
        rośnie wykładniczo z falą, więc rozjeżdżała się przy każdej zmianie
        wypłaty. Minuta gry znaczy to samo na fali 1 i na fali 25.
        """
        return self.cost_minutes * INCOME_AT_UNLOCK[self.unlock_wave]

    def cost_at_level(self, current_level: int) -> float:
        """Zwraca koszt zakupu następnego poziomu (od current_level do current_level+1)."""
        return self.base_cost * (self.cost_multiplier ** current_level)

    def current_level(self, state) -> int:
        """Zwraca aktualny poziom tego ulepszenia."""
        return getattr(state, f"upgrade_{self.id}")

    def is_maxed(self, state) -> bool:
        """Sprawdza czy ulepszenie jest na maksymalnym poziomie.

        Ulepszenie bez sufitu (`max_level is None`) nigdy nie jest maksymalne —
        to ono jest ujściem dla monet. Sufit oznacza skończoną pojemność
        wydatków, a przychód w tej grze rośnie bez końca.
        """
        if self.max_level is None:
            return False
        return self.current_level(state) >= self.max_level

    def can_afford(self, state) -> bool:
        """Sprawdza czy gracza stać na następny poziom."""
        return state.coins >= self.cost_at_level(self.current_level(state))

    def is_unlocked(self, state) -> bool:
        """Sprawdza czy wymaganie (requires) jest spełnione."""
        if self.requires is None:
            return True
        return getattr(state, f"upgrade_{self.requires}") > 0

    def purchase(self, state) -> bool:
        """Kupuje jeden poziom. Zwraca True jeśli zakup się powiódł."""
        if self.is_maxed(state) or not self.can_afford(state) or not self.is_unlocked(state):
            return False
        cost = self.cost_at_level(self.current_level(state))
        state.spend_coins(cost)
        attr = f"upgrade_{self.id}"
        setattr(state, attr, getattr(state, attr) + 1)
        return True


@dataclass
class PrestigeUpgrade:
    id: str
    name: str
    description: str
    max_level: int
    cost_crystals: int   # stały koszt w kryształach za poziom

    def current_level(self, state: "GameState") -> int:
        """Zwraca aktualny poziom ulepszenia prestige."""
        return getattr(state, f"prestige_{self.id}")

    def is_maxed(self, state: "GameState") -> bool:
        """Sprawdza czy osiągnięto maksymalny poziom."""
        return self.current_level(state) >= self.max_level

    def can_afford(self, state: "GameState") -> bool:
        """Sprawdza czy gracz ma wystarczająco kryształów."""
        return state.prestige_crystals >= self.cost_crystals

    def purchase(self, state: "GameState") -> bool:
        """Kupuje jeden poziom. Zwraca True jeśli zakup się powiódł."""
        if self.is_maxed(state) or not self.can_afford(state):
            return False
        state.spend_crystals(self.cost_crystals)
        attr = f"prestige_{self.id}"
        setattr(state, attr, getattr(state, attr) + 1)
        return True


PRESTIGE_UPGRADES: list[PrestigeUpgrade] = [
    PrestigeUpgrade("speed",      "Wrodzona prędkość", "+10% bazowej prędkości na start", 5, 2),
    PrestigeUpgrade("hole_size",  "Wyczucie dziury",   "+8° rozmiaru dziury na start",    5, 2),
    PrestigeUpgrade("coin_mult",  "Złota rączka",      "+25% monet permanentnie",         5, 3),
    PrestigeUpgrade("extra_ball", "Druga szansa",      "Dodatkowa piłka od startu",       2, 5),
]


UPGRADES: list[Upgrade] = [
    # Gałąź: Piłka
    Upgrade("ball_speed",  "Predkosc pilki", "+20% predkosci",             "ball", 5, 0.333),
    Upgrade("ball_size",   "Rozmiar pilki",  "Wieksza pilka = latwiej",    "ball", 3, 0.533, requires="ball_speed"),
    Upgrade("multi_ball",  "Multi-ball",     "Dodatkowa pilka na planszy", "ball", 3, 2.0,   requires="ball_speed"),
    Upgrade("ball_trail",  "Smuga",          "Efekt wizualny smugi",       "ball", 1, 1.0,   requires="ball_speed"),
    # Bez sufitu — ujście dla monet po wyczerpaniu reszty drzewka. Efekt mnożny,
    # bo HP okręgu rośnie liniowo z falą, a przy koszcie wykładniczym dodawanie
    # stałej dawałoby wzrost logarytmiczny, który nigdy by nie nadążył.
    Upgrade("ball_damage", "Sila uderzenia", "+25% obrazen za poziom",     "ball", None, 1.333,
            cost_multiplier=1.6, requires="ball_speed"),

    # Gałąź: Okręgi
    Upgrade("hole_size",  "Rozmiar dziury", "+10 stopni rozmiaru dziury", "rings", 5, 0.4),
    Upgrade("hole_count", "Liczba dziur",   "+1 dziura w okregu",         "rings", 3, 0.8,   requires="hole_size"),
    Upgrade("hole_speed", "Ruch dziury",    "Dziury sie obracaja",        "rings", 3, 0.667, requires="hole_size"),
    Upgrade("explosion",  "Eksplozja",      "+monety za zniszczenie",     "rings", 3, 0.533),

    # Gałąź: Ekonomia
    Upgrade("coin_multiplier", "Mnoznik monet",     "+50% monet za okrag",  "economy", 5, 0.667),
    Upgrade("auto_collector",  "Auto-kolektor",     "Monety same wpadaja",  "economy", 1, 3.333, requires="coin_multiplier"),
    Upgrade("coins_on_bounce", "Monety za odbicie", "+1% wyplaty za odbicie", "economy", 3, 1.0, requires="coin_multiplier"),
]

_validate_unlock_waves(UPGRADES)
