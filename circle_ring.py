import pygame
import math
import random
from config import Config
from ring_types import NORMAL, RingType


# Blokada po trafieniu w dziurę. Piłka przecina pasmo kolizji przez ~0,08 s,
# więc bez niej jeden przelot zadawałby kilka ciosów zamiast jednego.
HOLE_HIT_COOLDOWN: float = 0.2


class CircleRing:
    def __init__(self, config: Config, window_size: tuple, hp: int = 100,
                 ring_type: RingType = NORMAL) -> None:
        self.config = config
        self.type = ring_type
        self.cx = window_size[0] / 2
        self.cy = window_size[1] / 2
        self.radius: float = config.ring_start_radius
        self.alive = True
        self.thickness = ring_type.thickness
        self.max_hp: int = max(1, int(hp * ring_type.hp_multiplier))
        self.hp: int = self.max_hp
        self.base_color = ring_type.color
        self.color = self.base_color   # zmienia się z HP
        self.exploded = False  # flaga — cząsteczki emitowane tylko raz
        self.gold_multiplier: float = 1.0
        # Czy podział po śmierci został już rozliczony przez RingField
        self.split_resolved: bool = False

        # Fade out po zniszczeniu
        self.alpha: float = 255.0

        # Wygeneruj dziury równomiernie rozłożone, z losowym przesunięciem całości
        self.holes: list[float] = []
        if config.hole_count > 0:
            step = 360.0 / config.hole_count
            offset = random.uniform(0, 360)
            for i in range(config.hole_count):
                self.holes.append((offset + i * step) % 360)

    def hit(self, damage: int = 10) -> bool:
        """Wywołaj przy odbiciu piłki od okręgu.
        Zwraca True jeśli okrąg zniszczony przez ścieranie HP."""
        self.hp = max(0, self.hp - damage)
        self._update_color()
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def destroy(self) -> None:
        """Wywołaj gdy piłka trafi w dziurę — natychmiastowe zniszczenie."""
        self.hp = 0
        self.alive = False

    def _update_color(self) -> None:
        """Kolor przechodzi od barwy typu (pełne HP) do czerwieni (martwy)."""
        ratio = self.hp / self.max_hp  # 1.0 = pełne HP, 0.0 = martwe
        r0, g0, b0 = self.base_color
        dead = (220, 60, 60)
        self.color = (
            int(r0 + (dead[0] - r0) * (1.0 - ratio)),
            int(g0 + (dead[1] - g0) * (1.0 - ratio)),
            int(b0 + (dead[2] - b0) * (1.0 - ratio)),
        )

    def update(self, dt: float, speed_multiplier: float = 1.0) -> None:
        if not self.alive:
            self.alpha = max(0.0, self.alpha - 400 * dt)
            return

        if self.config.hole_moving:
            self.holes = [(h + self.config.hole_move_speed * dt) % 360
                          for h in self.holes]

        # Zmniejszanie — współczynnik prędkości (np. 0.05 gdy ice aktywny)
        self.radius -= (self.config.ring_shrink_speed * speed_multiplier
                        * self.type.shrink_multiplier * dt)

    def is_point_in_hole(self, angle_deg: float) -> bool:
        """Sprawdź czy kąt mieści się w którejś dziurze."""
        half = self.config.hole_size / 2
        for hole in self.holes:
            # Różnica kątów znormalizowana do zakresu -180..180
            diff = (angle_deg - hole + 180) % 360 - 180
            if abs(diff) <= half:
                return True
        return False

    def _swept_crossing(self, ball) -> float | None:
        """Ułamek odcinka ruchu piłki, na którym przecina ona linię okręgu.

        Test pozycyjny pyta tylko „gdzie piłka jest teraz" — piłce, która w
        jednym kroku przeskoczyła z jednej strony okręgu na drugą, wymyka się
        całkowicie. Tutaj rozwiązujemy |P0 + t*(P1-P0) - C|² = R² względem t
        i zwracamy najmniejsze t w [0, 1], czyli moment pierwszego kontaktu.
        Zwraca None, gdy odcinek w ogóle nie dosięga linii okręgu.
        """
        px = ball.prev_x - self.cx
        py = ball.prev_y - self.cy
        dx = ball.x - ball.prev_x
        dy = ball.y - ball.prev_y

        a = dx * dx + dy * dy
        if a < 1e-12:            # piłka stoi w miejscu
            return None

        b = 2.0 * (px * dx + py * dy)
        c = px * px + py * py - self.radius * self.radius
        delta = b * b - 4.0 * a * c
        if delta < 0.0:          # odcinek mija okrąg
            return None

        root = math.sqrt(delta)
        # a > 0, więc pierwszy pierwiastek jest zawsze mniejszy
        for t in ((-b - root) / (2.0 * a),
                  (-b + root) / (2.0 * a)):
            if 0.0 <= t <= 1.0:
                return t
        return None

    def check_collision(self, ball) -> bool:
        """
        Sprawdza kolizję piłki z okręgiem.
        Zwraca True jeśli nastąpiło odbicie od pełnej części.
        Jeśli piłka trafiła w dziurę — niszczy okrąg natychmiast, zwraca False.
        Odbicie od pełnej części zadaje 10 obrażeń; przy HP <= 0 okrąg zniszczony.
        """
        if not self.alive:
            return False

        dx = ball.x - self.cx
        dy = ball.y - self.cy
        dist = math.sqrt(dx * dx + dy * dy)

        # Kolizja gdy piłka dotyka powierzchni okręgu od wewnątrz lub zewnątrz
        swept = False
        if abs(dist - self.radius) > ball.radius + self.thickness:
            # Piłka nie dotyka okręgu teraz, ale mogła go przeskoczyć w trakcie kroku
            t = self._swept_crossing(ball)
            if t is None:
                return False
            # Cofnij piłkę do miejsca, w którym naprawdę dotknęła okręgu
            swept = True
            ball.x = ball.prev_x + (ball.x - ball.prev_x) * t
            ball.y = ball.prev_y + (ball.y - ball.prev_y) * t
            dx = ball.x - self.cx
            dy = ball.y - self.cy
            dist = math.sqrt(dx * dx + dy * dy)

        if dist < 0.001:
            return False

        angle = math.degrees(math.atan2(dy, dx)) % 360

        if self.is_point_in_hole(angle):
            # Dziura — piłka przelatuje bez odbicia, ale zadaje duży cios.
            # Zwracamy False także wtedy, gdy okrąg od tego ginie: pętla główna
            # po tym właśnie rozpoznaje "Dziura!" kontra "Zniszczony!".
            if ball.hole_cooldown <= 0.0:
                self.hit(self.config.ball_damage
                         * self.config.hole_damage_multiplier)
                ball.hole_cooldown = HOLE_HIT_COOLDOWN
            return False

        if ball.collision_cooldown > 0:
            return False

        # Normalna zawsze skierowana OD środka okręgu DO piłki
        nx = dx / dist
        ny = dy / dist

        # Z której strony nadleciała piłka. Po cofnięciu do punktu styku
        # dist == radius, więc dla trafień swept stronę zna tylko poprzednia pozycja.
        if swept:
            prev_dist = math.sqrt((ball.prev_x - self.cx) ** 2
                                  + (ball.prev_y - self.cy) ** 2)
            from_inside = prev_dist < self.radius
        else:
            from_inside = dist < self.radius

        # Piłka wewnątrz okręgu — wypchnij do środka (zmniejsz dist do radius - ball.radius - 1)
        if from_inside:
            ball.x = self.cx + nx * (self.radius - ball.radius - self.thickness - 1)
            ball.y = self.cy + ny * (self.radius - ball.radius - self.thickness - 1)
            # Odbij do środka: normalna wskazuje do środka = -nx, -ny
            ball.bounce_radial(-nx, -ny)
        else:
            # Piłka na zewnątrz — wypchnij na zewnątrz
            ball.x = self.cx + nx * (self.radius + ball.radius + self.thickness + 1)
            ball.y = self.cy + ny * (self.radius + ball.radius + self.thickness + 1)
            ball.bounce_radial(nx, ny)

        # Odbicie zadaje obrażenia
        self.hit(self.config.ball_damage)

        return True

    def _draw_band(self, surface: pygame.Surface,
                   color: tuple[int, int, int]) -> None:
        """Rysuje pełne części okręgu jako łuki — po jednym na odcinek.

        Wersja punktowa stawiała 360 kółek na okrąg, co przy pięciu okręgach
        kosztowało 2 ms na klatkę, czyli 12% budżetu przy 60 FPS. Łuki dają
        ten sam obraz 13 razy taniej.

        Prostokąt ma promień r+grubość, bo pygame rysuje łuk do wewnątrz od
        jego krawędzi, a pasmo ma być wyśrodkowane na linii okręgu tak jak
        przy kółkach. Kąty są negowane, bo ekranowy Y rośnie w dół i kąt w tej
        grze narasta zgodnie ze wskazówkami zegara, a pygame liczy przeciwnie.
        """
        half = self.config.hole_size / 2.0
        outer = self.radius + self.thickness
        width = self.thickness * 2
        centre = (int(self.cx), int(self.cy))

        # Brak dziur to warunek poprawności — bez tego nie powstałby żaden
        # łuk i okrąg zniknąłby. Dziura zerowej szerokości dałaby łuk pełnych
        # 360 stopni i wyglądałaby tak samo; to skrót wydajnościowy, bo
        # draw.circle jest 1,7x tańszy, a świeży gracz ma dokładnie taki okrąg.
        if not self.holes or half <= 0.0:
            pygame.draw.circle(surface, color, centre, int(outer), width)
            return

        rect = pygame.Rect(self.cx - outer, self.cy - outer, outer * 2, outer * 2)
        holes = sorted(h % 360.0 for h in self.holes)

        for i, hole in enumerate(holes):
            # Odstęp do następnej dziury; przy jednej dziurze okrąg zamyka się
            # sam, a modulo dałoby tu zero i skasowało cały okrąg.
            following = holes[(i + 1) % len(holes)]
            spacing = 360.0 if len(holes) == 1 else (following - hole) % 360.0
            span = spacing - 2.0 * half
            if span <= 0.0:          # dziury zachodzą na siebie
                continue

            start = (hole + half) % 360.0
            pygame.draw.arc(surface, color, rect,
                            math.radians(-(start + span)),
                            math.radians(-start), width)

    def is_faded(self) -> bool:
        """Zwraca True gdy okrąg jest martwy i całkowicie przezroczysty."""
        return not self.alive and self.alpha <= 0

    def draw(self, surface: pygame.Surface,
             font: pygame.font.Font | None = None) -> None:
        if self.alpha <= 0:
            return

        # Przyciemnij kolor proporcjonalnie do alpha
        if not self.alive:
            factor = self.alpha / 255.0
            color = tuple(int(c * factor) for c in self.color)
        else:
            color = self.color

        self._draw_band(surface, color)

        # Pasek HP: poziomy prostokąt pod okręgiem (tylko gdy żywy)
        if self.alive and self.max_hp > 0:
            bar_w = 60
            bar_h = 4
            bx = int(self.cx - bar_w // 2)
            by = int(self.cy + self.radius + 8)
            pygame.draw.rect(surface, (50, 50, 65), (bx, by, bar_w, bar_h))
            fill_w = max(0, int(bar_w * self.hp / self.max_hp))
            if fill_w > 0:
                pygame.draw.rect(surface, self.color, (bx, by, fill_w, bar_h))

        # Etykieta typu pod paskiem HP — przy pięciu typach sam kolor
        # byłby zagadką. Zwykły okrąg ma pustą nazwę i nie dostaje etykiety.
        if self.alive and font is not None and self.type.name:
            label = font.render(self.type.name, True, self.base_color)
            surface.blit(label, label.get_rect(
                centerx=int(self.cx),
                top=int(self.cy + self.radius + 16)))
