from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Upgrade:
    id: str
    name: str
    description: str
    branch: str           # "ball" | "rings" | "economy"
    max_level: int
    base_cost: float      # koszt pierwszego poziomu
    cost_multiplier: float = 2.0  # każdy poziom droższy x razy
    requires: Optional[str] = None   # id innego upgrade który musi być > 0

    def cost_at_level(self, current_level: int) -> float:
        """Zwraca koszt zakupu następnego poziomu (od current_level do current_level+1)."""
        return self.base_cost * (self.cost_multiplier ** current_level)

    def current_level(self, state) -> int:
        """Zwraca aktualny poziom tego ulepszenia."""
        return getattr(state, f"upgrade_{self.id}")

    def is_maxed(self, state) -> bool:
        """Sprawdza czy ulepszenie jest na maksymalnym poziomie."""
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


UPGRADES: list[Upgrade] = [
    # Gałąź: Piłka
    Upgrade("ball_speed",    "Prędkość piłki",    "+20% prędkości",            "ball",    5, 50.0),
    Upgrade("ball_size",     "Rozmiar piłki",     "Większa piłka = łatwiej",   "ball",    3, 80.0,  requires="ball_speed"),
    Upgrade("multi_ball",    "Multi-ball",        "Dodatkowa piłka na planszy", "ball",   2, 300.0, requires="ball_speed"),
    Upgrade("ball_trail",    "Smuga",             "Efekt wizualny smugi",       "ball",   1, 150.0, requires="ball_speed"),

    # Gałąź: Okręgi
    Upgrade("hole_size",     "Rozmiar dziury",    "+10° rozmiar dziury",        "rings",  5, 60.0),
    Upgrade("hole_count",    "Liczba dziur",      "+1 dziura w okręgu",         "rings",  3, 120.0, requires="hole_size"),
    Upgrade("hole_speed",    "Ruch dziury",       "Dziury się obracają",        "rings",  3, 100.0, requires="hole_size"),
    Upgrade("explosion",     "Eksplozja",         "+monety za zniszczenie",     "rings",  3, 80.0),

    # Gałąź: Ekonomia
    Upgrade("coin_multiplier", "Mnożnik monet",   "+50% monet za okrąg",        "economy", 5, 100.0),
    Upgrade("auto_collector",  "Auto-kolektor",   "Monety same wpadają",        "economy", 1, 500.0, requires="coin_multiplier"),
    Upgrade("coins_on_bounce", "Monety za odbicie", "+0.5 monet za odbicie",    "economy", 3, 150.0, requires="coin_multiplier"),
]
