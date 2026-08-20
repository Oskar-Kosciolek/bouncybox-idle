class ConfirmedAction:
    """Akcja wymagająca dwóch wywołań w krótkim oknie czasowym.

    Czas wstrzykiwany, nie odczytywany z zegara — inaczej test okna
    potwierdzenia musiałby czekać po sekundzie na każdy przypadek.

    Jeden obiekt obsługuje wszystkie drogi do tej samej akcji (przycisk
    i skrót klawiszowy). Dwa osobne dałyby dwa niezależne uzbrojenia:
    gracz uzbroiłby przyciskiem, a klawisz kasowałby od razu.
    """

    def __init__(self, window_seconds: float = 3.0) -> None:
        self.window_seconds = window_seconds
        self._armed_until: float = 0.0

    def request(self, now: float) -> bool:
        """Zwraca True, gdy akcja ma się wykonać; False, gdy dopiero uzbroiła.

        Odpalenie rozbraja, więc trzecie wywołanie zaczyna od nowa —
        bez tego seria kliknięć kasowałaby postęp raz za razem.
        """
        if now < self._armed_until:
            self._armed_until = 0.0
            return True
        self._armed_until = now + self.window_seconds
        return False

    def is_armed(self, now: float) -> bool:
        """Czy trwa okno potwierdzenia — do rysowania stanu przycisku."""
        return now < self._armed_until

    def cancel(self) -> None:
        """Gasi uzbrojenie przed czasem."""
        self._armed_until = 0.0
