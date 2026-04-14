from dataclasses import dataclass


@dataclass
class GameState:
    coins: float = 0.0
    total_coins_earned: float = 0.0
    rings_destroyed: int = 0
    wave: int = 1
    rings_to_next_wave: int = 5   # ile okręgów do kolejnej fali
    rings_destroyed_this_wave: int = 0

    # Gałąź: Piłka
    upgrade_ball_speed: int = 0       # max 5
    upgrade_ball_size: int = 0        # max 3
    upgrade_multi_ball: int = 0       # max 2 (0=1 piłka, 1=2 piłki, 2=3 piłki)
    upgrade_ball_trail: int = 0       # max 1

    # Gałąź: Okręgi
    upgrade_hole_size: int = 0        # max 5
    upgrade_hole_count: int = 0       # max 3
    upgrade_hole_speed: int = 0       # max 3
    upgrade_explosion: int = 0        # max 3 (więcej cząsteczek = więcej monet)

    # Gałąź: Ekonomia
    upgrade_coin_multiplier: int = 0  # max 5
    upgrade_auto_collector: int = 0   # max 1
    upgrade_coins_on_bounce: int = 0  # max 3

    def add_coins(self, amount: float) -> None:
        """Dodaje monety z uwzględnieniem mnożnika."""
        multiplier = 1.0 + self.upgrade_coin_multiplier * 0.5
        earned = amount * multiplier
        self.coins += earned
        self.total_coins_earned += earned

    def spend_coins(self, amount: float) -> bool:
        """Wydaje monety. Zwraca True jeśli transakcja się powiodła."""
        if self.coins >= amount:
            self.coins -= amount
            return True
        return False

    def on_ring_destroyed(self) -> float:
        """Wywołaj gdy okrąg zostanie zniszczony. Zwraca ile monet przyznano."""
        self.rings_destroyed += 1
        self.rings_destroyed_this_wave += 1
        base_coins = 10.0 + self.wave * 5.0
        explosion_bonus = 1.0 + self.upgrade_explosion * 0.3
        coins = base_coins * explosion_bonus
        self.add_coins(coins)
        return coins

    def on_bounce(self) -> None:
        """Wywołaj przy każdym odbiciu jeśli upgrade_coins_on_bounce > 0."""
        if self.upgrade_coins_on_bounce > 0:
            self.add_coins(self.upgrade_coins_on_bounce * 0.5)

    def check_wave_progress(self) -> bool:
        """Zwraca True jeśli awansowano na nową falę."""
        if self.rings_destroyed_this_wave >= self.rings_to_next_wave:
            self.wave += 1
            self.rings_destroyed_this_wave = 0
            self.rings_to_next_wave = 5 + self.wave * 2
            return True
        return False
