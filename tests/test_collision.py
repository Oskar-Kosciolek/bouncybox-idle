from ball import Ball
from circle_ring import CircleRing
from config import Config

STEP = 1 / 240


def _board() -> tuple[Config, CircleRing]:
    """Okrąg o promieniu 220 wyśrodkowany w (200, 200)."""
    config = Config()
    return config, CircleRing(config, (400, 400))


def test_ball_jumping_over_ring_in_one_step_still_bounces():
    """Piłka pokonująca w jednym kroku więcej niż szerokość pasma kolizji
    musi się odbić, a nie znaleźć po drugiej stronie. Bez tego prędkość
    piłki ma ukryty sufit wyznaczony przez grubość okręgu."""
    config, ring = _board()
    ball = Ball(200.0, -60.0, config)      # 260 px nad środkiem, na zewnątrz
    ball.vx, ball.vy = 0.0, 80.0 / STEP    # 80 px na krok — przeskakuje linię

    ball.update(STEP)

    assert ring.check_collision(ball) is True


def test_bounced_ball_stays_on_the_side_it_came_from():
    """Odbicie ma odesłać piłkę na zewnątrz, a nie przepuścić ją do środka."""
    config, ring = _board()
    ball = Ball(200.0, -60.0, config)
    ball.vx, ball.vy = 0.0, 80.0 / STEP

    ball.update(STEP)
    ring.check_collision(ball)

    distance = ((ball.x - ring.cx) ** 2 + (ball.y - ring.cy) ** 2) ** 0.5
    assert distance > ring.radius


def test_ball_jumping_through_hole_still_registers_the_hit():
    """Trafienie w dziurę liczy się także wtedy, gdy piłka przeskoczyła
    przez nią w jednym kroku. Okrąg ma tu HP mieszczące się w jednym ciosie,
    bo dziura zadaje obrażenia, a nie zabija natychmiast."""
    config, ring = _board()
    config.hole_count = 1
    config.hole_size = 40.0
    ring.holes = [270.0]                   # dziura na górze okręgu
    ring.max_hp = ring.hp = 5
    ball = Ball(200.0, -60.0, config)
    ball.vx, ball.vy = 0.0, 80.0 / STEP

    ball.update(STEP)
    ring.check_collision(ball)

    assert ring.alive is False


def test_slow_ball_at_surface_still_bounces():
    """Regresja: zwykłe odbicie ma działać jak dotąd."""
    config, ring = _board()
    ball = Ball(200.0, 200.0 - 218.0, config)   # tuż przy linii, od wewnątrz
    ball.vx, ball.vy = 0.0, -100.0

    ball.update(STEP)

    assert ring.check_collision(ball) is True


def test_ball_far_from_ring_does_not_collide():
    """Regresja: brak fałszywych trafień, gdy odcinek ruchu nie sięga okręgu."""
    config, ring = _board()
    ball = Ball(200.0, 200.0, config)       # w samym środku
    ball.vx, ball.vy = 10.0, 0.0

    ball.update(STEP)

    assert ring.check_collision(ball) is False


def test_ball_tunneling_outward_is_sent_back_inside():
    """Piłka przeskakująca okrąg od środka na zewnątrz ma wrócić do wnętrza."""
    config, ring = _board()
    ball = Ball(200.0, 200.0 - 180.0, config)   # 180 px nad środkiem, wewnątrz
    ball.vx, ball.vy = 0.0, -80.0 / STEP        # w górę, przez linię okręgu

    ball.update(STEP)
    ring.check_collision(ball)

    distance = ((ball.x - ring.cx) ** 2 + (ball.y - ring.cy) ** 2) ** 0.5
    assert distance < ring.radius


def _ring_with_hole(hp: int = 100, ring_type=None):
    """Okrąg z dziurą na górze (kąt 270) — tam, gdzie przelatuje piłka."""
    from ring_types import NORMAL

    config = Config()
    config.hole_count = 1
    config.hole_size = 40.0
    ring = CircleRing(config, (400, 400), hp=hp,
                      ring_type=ring_type if ring_type else NORMAL)
    ring.holes = [270.0]
    return config, ring


def _cross_the_hole(config, ring) -> None:
    """Przepuszcza świeżą piłkę przez dziurę jednym skokiem."""
    ball = Ball(200.0, -60.0, config)
    ball.vx, ball.vy = 0.0, 80.0 / STEP
    ball.update(STEP)
    ring.check_collision(ball)


def test_hole_hit_damages_the_ring_instead_of_destroying_it():
    """Natychmiastowe zabicie sprawiało, że dziura zawsze strzelała pierwsza:
    w godzinnym pomiarze 2877 z 2915 zabójstw szło przez dziurę, więc
    ulepszenia obrażeń nie miały żadnego wpływu na rozgrywkę."""
    config, ring = _ring_with_hole(hp=100)

    _cross_the_hole(config, ring)

    assert ring.alive is True
    assert ring.hp == 100 - config.ball_damage * config.hole_damage_multiplier


def test_hole_hit_still_kills_a_ring_it_can_finish():
    config, ring = _ring_with_hole(hp=10)

    _cross_the_hole(config, ring)

    assert ring.alive is False


def test_hole_hit_registers_once_per_pass():
    """Piłka siedzi w paśmie kolizji przez kilka kroków fizyki. Bez osobnego
    licznika jeden przelot dawałby kilka trafień zamiast jednego."""
    config, ring = _ring_with_hole(hp=1000)
    ball = Ball(200.0, -60.0, config)
    ball.vx, ball.vy = 0.0, 80.0 / STEP
    ball.update(STEP)

    ring.check_collision(ball)
    hp_after_first = ring.hp
    ring.check_collision(ball)

    assert ring.hp == hp_after_first


def test_armoured_ring_needs_more_hole_hits_than_a_normal_one():
    """Sedno zmiany: typ okręgu ma znów cokolwiek znaczyć."""
    from ring_types import ARMORED, NORMAL

    def hits_to_kill(ring_type) -> int:
        config, ring = _ring_with_hole(hp=100, ring_type=ring_type)
        hits = 0
        while ring.alive and hits < 200:
            _cross_the_hole(config, ring)
            hits += 1
        return hits

    assert hits_to_kill(ARMORED) > hits_to_kill(NORMAL)
