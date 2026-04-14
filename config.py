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
    ball_radius: int = 10

    # Fizyka odbicia
    restitution: float = 1.0  # 1.0 = idealne, <1.0 = traci energię

    # Okręgi
    ring_spawn_interval: float = 3.0   # sekundy między nowymi okręgami
    ring_shrink_speed: float = 30.0    # px/s — prędkość zmniejszania się
    ring_start_radius: float = 220.0   # promień startowy
    ring_min_radius: float = 30.0      # minimalna wielkość

    # Dziury
    hole_count: int = 1                # liczba dziur na okręgu (1-4)
    hole_size: float = 45.0            # rozmiar dziury w stopniach
    hole_moving: bool = False          # czy dziura się porusza
    hole_move_speed: float = 60.0      # deg/s — prędkość ruchu dziury

    # Efekty wizualne
    ball_trail_enabled: bool = False   # czy rysować smugę za piłką

    def apply_upgrades(self, state) -> None:
        """Aktualizuje pola config na podstawie aktualnych poziomów ulepszeń."""
        base_speed = 200.0
        speed = base_speed * (1.0 + state.upgrade_ball_speed * 0.2)
        self.initial_speed_x = speed
        self.initial_speed_y = -speed
        self.ball_radius = 8 + state.upgrade_ball_size * 2
        self.hole_size = 45.0 + state.upgrade_hole_size * 10.0
        self.hole_count = 1 + state.upgrade_hole_count
        self.hole_moving = state.upgrade_hole_speed > 0
        self.hole_move_speed = state.upgrade_hole_speed * 25.0
        self.ball_trail_enabled = state.upgrade_ball_trail > 0
        # Trudność rośnie z falą
        self.ring_shrink_speed = 25.0 + state.wave * 3.0
        self.ring_spawn_interval = max(1.0, 4.0 - state.wave * 0.2)
