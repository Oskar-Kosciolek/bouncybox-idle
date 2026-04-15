from dataclasses import dataclass


@dataclass
class Config:
    # Prędkość startowa piłki
    initial_speed_x: float = 200.0
    initial_speed_y: float = -150.0

    # Grawitacja
    gravity_enabled: bool = False
    gravity_strength: float = 400.0   # px/s²

    # Piłeczka
    ball_speed: float = 200.0
    ball_radius: int = 5
    ball_damage: int = 1

    # Fizyka odbicia
    restitution: float = 1.0  # 1.0 = idealne, <1.0 = traci energię

    # Okręgi
    ring_spawn_interval: float = 3.0   # sekundy między nowymi okręgami
    ring_shrink_speed: float = 1.0    # px/s — prędkość zmniejszania się
    ring_start_radius: float = 220.0   # promień startowy
    ring_min_radius: float = 100.0      # minimalna wielkość

    # Dziury
    hole_count: int = 0                # liczba dziur na okręgu (1-4)
    hole_size: float = 0.0             # rozmiar dziury w stopniach (małe — złoty strzał)
    hole_moving: bool = False          # czy dziura się porusza
    hole_move_speed: float = 10.0      # deg/s — prędkość ruchu dziury

    # Efekty wizualne
    ball_trail_enabled: bool = False   # czy rysować smugę za piłką

    def apply_upgrades(self, state) -> None:
        """Aktualizuje pola config na podstawie aktualnych poziomów ulepszeń i prestige."""
        # Prestige bonusy (permanentne)
        prestige_speed_bonus = 1.0 + state.prestige_speed * 0.10
        prestige_hole_bonus = state.prestige_hole_size * 8.0

        base_speed = self.ball_speed + 20 * prestige_speed_bonus
        speed = base_speed * (1.0 + state.upgrade_ball_speed * 0.2)
        self.initial_speed_x = speed
        self.initial_speed_y = -speed
        self.ball_radius = self.ball_radius + state.upgrade_ball_size * 2
        self.hole_size = self.hole_size + state.upgrade_hole_size * 10.0 + prestige_hole_bonus
        self.hole_count = self.hole_count + state.upgrade_hole_count
        self.hole_moving = state.upgrade_hole_speed > 0
        self.hole_move_speed = self.hole_move_speed + state.upgrade_hole_speed * 25.0
        self.ball_trail_enabled = state.upgrade_ball_trail > 0
        # Trudność rośnie z falą
        self.ring_shrink_speed = self.ring_shrink_speed + state.wave * 3.0
        self.ring_spawn_interval = max(1.0, 4.0 - state.wave * 0.2)
