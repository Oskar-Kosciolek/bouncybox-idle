from timestep import FixedTimestep


def test_simulation_keeps_up_with_wall_clock_at_60_fps():
    """10 sekund realnych = 10 sekund symulacji. Poprzedni `min(dt, 0.01)`
    przy 60 FPS ścinał każdą klatkę do 0.01 s i dawał 6 s zamiast 10."""
    timer = FixedTimestep()
    frame = 1 / 60

    steps = sum(timer.steps(frame) for _ in range(600))
    simulated_time = steps * timer.step

    assert abs(simulated_time - 10.0) < timer.step


def test_leftover_carries_over_to_next_frame():
    """Klatka krótsza od kroku fizyki nie znika — kumuluje się."""
    timer = FixedTimestep()
    half_step = timer.step / 2

    assert timer.steps(half_step) == 0
    assert timer.steps(half_step) == 1


def test_long_stall_does_not_cause_death_spiral():
    """Po 2-sekundowej zwiesze (np. przeciąganie okna) nie nadrabiamy
    480 kroków w jednej klatce — to zawiesiłoby grę na dobre."""
    timer = FixedTimestep()

    steps = timer.steps(2.0)

    assert 0 < steps <= timer.max_steps


def test_dropped_backlog_does_not_return_in_later_frames():
    """Porzucona zaległość musi zniknąć, inaczej gra nadrabia ją w nieskończoność."""
    timer = FixedTimestep()
    timer.steps(2.0)

    steps = timer.steps(1 / 60)

    assert 0 < steps <= timer.max_steps
