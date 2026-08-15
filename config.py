from dataclasses import dataclass

# Wartości bazowe pól POCHODNYCH — tych, które wylicza apply_upgrades.
# apply_upgrades startuje od nich za każdym razem, dzięki czemu jest
# idempotentne: wielokrotne wywołanie daje ten sam wynik.
BASE_BALL_RADIUS: int = 5

# Okrąg ma od startu jedną dziurę o ZEROWEJ szerokości. Liczba, bo drzewko
# wymaga kupienia `hole_size` przed `hole_count`, a rozmiar bez choćby jednej
# dziury nie robi nic — pierwszy zakup w tej gałęzi byłby pustym wydatkiem.
# Szerokość zero, bo dziura na starcie psuła balans: przy 77 odbiciach na
# fali 1 darmowy zabój trafiał się niemal na pewno i ulepszenia dziur traciły
# sens. Świeży gracz dobija okręgi karencją przed zduszeniem (crush_grace).
BASE_HOLE_SIZE: float = 0.0
BASE_HOLE_COUNT: int = 1
BASE_HOLE_MOVE_SPEED: float = 10.0
BASE_RING_SHRINK_SPEED: float = 1.0

# Łączne pokrycie dziurami nie może domknąć okręgu. Przy maksymalnych
# ulepszeniach wychodziły 4 dziury po 100°, czyli 400° na obwodzie 360° —
# nie zostawał ani jeden lity stopień, okrąg ginął od pierwszego dotknięcia,
# a HP, pancerz i boss przestawały cokolwiek znaczyć.
MAX_HOLE_COVERAGE: float = 300.0

# Sufit prędkości zwężania. Póki okręgi żyły w nieskończoność, ten parametr
# sterował wyłącznie tempem gry i mógł rosnąć bez granic. Odkąd okrąg dojeżdża
# do minimum i dusi piłkę, steruje też śmiertelnością: liniowy wzrost 1+3*fala
# skracał życie okręgu do 1,6 s na fali 30, czyli 3 odbić zamiast kilkunastu.
# Trudność ma dalej rosnąć, ale przez HP i typy okręgów, nie przez odbieranie
# graczowi czasu na reakcję.
MAX_RING_SHRINK_SPEED: float = 25.0


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
    ring_min_radius: float = 30.0      # minimalna wielkość
    ring_max_active: int = 5           # ile okręgów naraz na planszy

    # Ile sekund okrąg stoi na minimalnym promieniu, zanim zdusi piłkę.
    # Przy minimum piłka odbija się ~5 razy na sekundę, więc karencja jest
    # oknem na dobicie okręgu bez dziur. Starcza na fali 1 (potrzeba 4,3 s),
    # nie starcza od fali 2 (13,6 s) — i to jest moment, w którym gracz
    # musi sięgnąć po ulepszenia dziur.
    crush_grace: float = 6.0

    # Wejścia dla pól pochodnych. Suwaki w panelu Ustawienia sterują właśnie
    # nimi, a nie ring_shrink_speed czy ring_spawn_interval — te dwa są
    # przeliczane przy każdym zakupie i awansie fali, więc wartość wpisana
    # w nie wprost znikała przy najbliższej okazji.
    shrink_per_wave: float = 3.0
    max_shrink_speed: float = MAX_RING_SHRINK_SPEED
    min_spawn_interval: float = 1.0

    # Dziury
    hole_count: int = 0                # liczba dziur na okręgu (1-4)
    hole_size: float = 0.0             # rozmiar dziury w stopniach (małe — złoty strzał)
    hole_moving: bool = False          # czy dziura się porusza
    hole_move_speed: float = 10.0      # deg/s — prędkość ruchu dziury

    # Efekty wizualne
    ball_trail_enabled: bool = False   # czy rysować smugę za piłką

    # Power-upy
    powerup_duration: float = 10.0        # czas wyświetlania na planszy (s)
    powerup_max_visible: int = 2          # max jednocześnie widocznych
    powerup_spawn_radius: float = 150.0   # promień strefy spawnu (koło od środka)
    powerup_spawn_interval: float = 8.0   # co ile sekund próba spawnu

    # Szanse spawnu per typ (0.0 - 1.0)
    powerup_chance_gold: float = 0.3
    powerup_chance_bomb: float = 0.2
    powerup_chance_ice: float = 0.2
    powerup_chance_mystery: float = 0.15

    def apply_upgrades(self, state) -> None:
        """Przelicza pola pochodne na podstawie poziomów ulepszeń, prestige i fali.

        Idempotentne — każde pole liczone jest od wartości BASE_*, nigdy od
        własnej poprzedniej wartości. Metoda jest wołana przy każdym zakupie,
        awansie fali, prestige i wczytaniu zapisu, więc kumulowanie zamieniało
        balans w potęgę (fala 10 → shrink 178 px/s, dziura 600°).
        """
        # Prestige bonusy (permanentne)
        prestige_speed_bonus = 1.0 + state.prestige_speed * 0.10
        prestige_hole_bonus = state.prestige_hole_size * 8.0

        base_speed = self.ball_speed + 20 * prestige_speed_bonus
        speed = base_speed * (1.0 + state.upgrade_ball_speed * 0.2)
        self.initial_speed_x = speed
        self.initial_speed_y = -speed
        self.ball_radius = BASE_BALL_RADIUS + state.upgrade_ball_size * 2
        # Liczba dziur przed rozmiarem — sufit rozmiaru zależy od liczby
        self.hole_count = BASE_HOLE_COUNT + state.upgrade_hole_count
        raw_hole_size = (BASE_HOLE_SIZE + state.upgrade_hole_size * 10.0
                         + prestige_hole_bonus)
        self.hole_size = min(raw_hole_size,
                             MAX_HOLE_COVERAGE / self.hole_count)
        self.hole_moving = state.upgrade_hole_speed > 0
        self.hole_move_speed = (BASE_HOLE_MOVE_SPEED
                                + state.upgrade_hole_speed * 25.0)
        self.ball_trail_enabled = state.upgrade_ball_trail > 0
        # Trudność rośnie z falą, ale zwężanie ma sufit
        self.ring_shrink_speed = min(
            BASE_RING_SHRINK_SPEED + state.wave * self.shrink_per_wave,
            self.max_shrink_speed)
        self.ring_spawn_interval = max(self.min_spawn_interval,
                                       4.0 - state.wave * 0.2)
