from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    reward_coins: float
    reward_crystals: int = 0

    def check(self, state: "GameState") -> bool:
        """Zwraca True jeśli warunek osiągnięcia jest spełniony."""
        from upgrade_tree import UPGRADES  # import lokalny — unika cyklu

        if self.id == "first_ring":
            return state.rings_destroyed >= 10
        elif self.id == "ring_100":
            return state.rings_destroyed >= 100
        elif self.id == "ring_500":
            return state.rings_destroyed >= 500
        elif self.id == "wave_5":
            return state.wave >= 5
        elif self.id == "wave_10":
            return state.wave >= 10
        elif self.id == "wave_20":
            return state.wave >= 20
        elif self.id == "upgrades_5":
            total = sum(getattr(state, f"upgrade_{u.id}") for u in UPGRADES)
            return total >= 5
        elif self.id == "upgrades_all":
            return all(
                getattr(state, f"upgrade_{u.id}") >= u.max_level
                for u in UPGRADES
            )
        elif self.id == "first_prestige":
            return state.prestige_count >= 1
        elif self.id == "prestige_5":
            return state.prestige_count >= 5
        elif self.id == "coins_1000":
            return state.achievement_coins_earned >= 1000
        elif self.id == "coins_100000":
            return state.achievement_coins_earned >= 100_000
        return False


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first_ring",     "Pierwsze kroki",    "Zniszcz 10 okręgów",              50.0),
    Achievement("ring_100",       "Pogromca",          "Zniszcz 100 okręgów",            300.0),
    Achievement("ring_500",       "Niszczyciel",       "Zniszcz 500 okręgów",           1000.0),
    Achievement("wave_5",         "Fala uderzeniowa",  "Dobij do fali 5",                200.0),
    Achievement("wave_10",        "Nieustępliwy",      "Dobij do fali 10",               500.0, reward_crystals=1),
    Achievement("wave_20",        "Legenda",           "Dobij do fali 20",              2000.0, reward_crystals=3),
    Achievement("upgrades_5",     "Kolekcjoner",       "Kup 5 ulepszeń",                 100.0),
    Achievement("upgrades_all",   "Kompletny",         "Kup wszystkie ulepszenia",      1000.0, reward_crystals=2),
    Achievement("first_prestige", "Wielki Wybuch",     "Wykonaj pierwszy prestige",        0.0, reward_crystals=3),
    Achievement("prestige_5",     "Feniks",            "Wykonaj 5 prestigeów",             0.0, reward_crystals=10),
    Achievement("coins_1000",     "Bogacz",            "Zarobij łącznie 1000 monet",     150.0),
    Achievement("coins_100000",   "Milioner",          "Zarobij łącznie 100000 monet",  5000.0, reward_crystals=2),
]


def check_achievements(state: "GameState") -> list[Achievement]:
    """Sprawdza niespełnione osiągnięcia i przyznaje nagrody za nowo odblokowane.

    Zwraca listę nowo odblokowanych osiągnięć (do wyświetlenia powiadomień).
    """
    newly_unlocked: list[Achievement] = []

    for ach in ACHIEVEMENTS:
        if ach.id in state.achievements_unlocked:
            continue  # już odblokowane

        if ach.check(state):
            state.achievements_unlocked.add(ach.id)
            # Przyznaj nagrodę w monetach
            if ach.reward_coins > 0:
                state.add_coins(ach.reward_coins)
            # Przyznaj kryształy prestige
            if ach.reward_crystals > 0:
                state.prestige_crystals += ach.reward_crystals
                state.prestige_crystals_total += ach.reward_crystals
            newly_unlocked.append(ach)

    return newly_unlocked
