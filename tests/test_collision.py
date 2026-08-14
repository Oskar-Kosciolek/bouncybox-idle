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


def test_ball_jumping_through_hole_destroys_ring():
    """Trafienie w dziurę liczy się także wtedy, gdy piłka przeskoczyła
    przez nią w jednym kroku."""
    config, ring = _board()
    config.hole_count = 1
    config.hole_size = 40.0
    ring.holes = [270.0]                   # dziura na górze okręgu
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
