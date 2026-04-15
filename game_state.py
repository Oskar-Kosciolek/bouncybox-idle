from dataclasses import dataclass, field


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

    # Prestige
    prestige_count: int = 0
    prestige_crystals: int = 0
    prestige_crystals_total: int = 0

    # Prestige upgrades (permanentne, nie resetują się)
    prestige_speed: int = 0        # max 5, +10% base_speed za poziom
    prestige_hole_size: int = 0    # max 5, +8° hole_size za poziom
    prestige_coin_mult: int = 0    # max 5, +25% monet za poziom
    prestige_extra_ball: int = 0   # max 2, dodatkowa piłka od startu

    # Osiągnięcia — set odblokowanych id
    achievements_unlocked: set = field(default_factory=set)
    achievement_coins_earned: float = 0.0  # osobny licznik do osiągnięć (bez mnożników)

    def add_coins(self, amount: float) -> None:
        """Dodaje monety z uwzględnieniem mnożnika upgradeów i prestige."""
        upgrade_mult = 1.0 + self.upgrade_coin_multiplier * 0.5
        prestige_mult = 1.0 + self.prestige_coin_mult * 0.25
        earned = amount * upgrade_mult * prestige_mult
        self.coins += earned
        self.total_coins_earned += earned
        self.achievement_coins_earned += amount  # bez mnożników, do osiągnięć

    def spend_coins(self, amount: float) -> bool:
        """Wydaje monety. Zwraca True jeśli transakcja się powiodła."""
        if self.coins >= amount:
            self.coins -= amount
            return True
        return False

    def spend_crystals(self, amount: int) -> bool:
        """Wydaje kryształy prestige. Zwraca True jeśli transakcja się powiodła."""
        if self.prestige_crystals >= amount:
            self.prestige_crystals -= amount
            return True
        return False

    def prestige(self) -> bool:
        """Wykonuje prestige. Wymaga fali >= 10. Zwraca True jeśli się powiodło."""
        if self.wave < 10:
            return False

        # Oblicz liczbę kryształów do zdobycia
        crystals = 1 + self.prestige_count // 2

        # Zachowaj permanentne pola przed resetem
        saved_prestige_count = self.prestige_count
        saved_prestige_crystals = self.prestige_crystals
        saved_prestige_crystals_total = self.prestige_crystals_total
        saved_prestige_speed = self.prestige_speed
        saved_prestige_hole_size = self.prestige_hole_size
        saved_prestige_coin_mult = self.prestige_coin_mult
        saved_prestige_extra_ball = self.prestige_extra_ball
        saved_achievements_unlocked = self.achievements_unlocked
        saved_achievement_coins_earned = self.achievement_coins_earned

        # Zresetuj wszystkie pola do wartości domyślnych
        defaults = GameState()
        for attr, val in defaults.__dict__.items():
            setattr(self, attr, val)

        # Przywróć permanentne pola
        self.prestige_count = saved_prestige_count
        self.prestige_crystals = saved_prestige_crystals
        self.prestige_crystals_total = saved_prestige_crystals_total
        self.prestige_speed = saved_prestige_speed
        self.prestige_hole_size = saved_prestige_hole_size
        self.prestige_coin_mult = saved_prestige_coin_mult
        self.prestige_extra_ball = saved_prestige_extra_ball
        self.achievements_unlocked = saved_achievements_unlocked
        self.achievement_coins_earned = saved_achievement_coins_earned

        # Dodaj kryształy i zwiększ licznik prestige
        self.prestige_crystals += crystals
        self.prestige_crystals_total += crystals
        self.prestige_count += 1

        return True

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

    def get_ring_hp(self) -> int:
        """Startowe HP okręgu = 100, rośnie o 15 za każdą falę."""
        return 100 + (self.wave - 1) * 15

    def check_wave_progress(self) -> bool:
        """Zwraca True jeśli awansowano na nową falę."""
        if self.rings_destroyed_this_wave >= self.rings_to_next_wave:
            self.wave += 1
            self.rings_destroyed_this_wave = 0
            self.rings_to_next_wave = 5 + self.wave * 2
            return True
        return False
