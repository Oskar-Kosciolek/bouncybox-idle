from confirm import ConfirmedAction


def test_the_first_request_only_arms():
    """Jedno wciśnięcie nie może kasować postępu — F5 leży obok F6."""
    action = ConfirmedAction(window_seconds=3.0)

    assert action.request(now=100.0) is False


def test_a_second_request_inside_the_window_fires():
    action = ConfirmedAction(window_seconds=3.0)
    action.request(now=100.0)

    assert action.request(now=102.9) is True


def test_a_second_request_after_the_window_only_arms_again():
    action = ConfirmedAction(window_seconds=3.0)
    action.request(now=100.0)

    assert action.request(now=103.1) is False


def test_firing_disarms_so_the_next_request_starts_over():
    """Bez rozbrojenia trzeci klik kasowałby drugi raz z rzędu."""
    action = ConfirmedAction(window_seconds=3.0)
    action.request(now=100.0)
    action.request(now=101.0)

    assert action.request(now=101.5) is False


def test_armed_state_expires_on_its_own():
    action = ConfirmedAction(window_seconds=3.0)
    action.request(now=100.0)

    assert action.is_armed(now=102.9) is True
    assert action.is_armed(now=103.1) is False


def test_a_fresh_action_is_not_armed():
    assert ConfirmedAction().is_armed(now=100.0) is False


def test_cancel_disarms():
    """Zmiana zakładki ma gasić uzbrojenie — inaczej wraca się do
    Ustawień po minucie i jeden klik kasuje grę."""
    action = ConfirmedAction(window_seconds=3.0)
    action.request(now=100.0)

    action.cancel()

    assert action.is_armed(now=100.5) is False
