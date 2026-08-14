class FixedTimestep:
    """Akumulator stałego kroku fizyki.

    Oddziela tempo symulacji od liczby klatek na sekundę: pętla renderuje
    ile zdąży, a fizyka posuwa się zawsze porcjami po `step` sekund.
    Dzięki temu zachowanie gry nie zależy od wydajności maszyny.
    """

    def __init__(self, step: float = 1 / 240, max_steps: int = 8) -> None:
        self.step = step
        self.max_steps = max_steps
        self._accumulator: float = 0.0

    def steps(self, frame_dt: float) -> int:
        """Ile kroków fizyki wykonać po klatce trwającej `frame_dt` sekund.

        Reszta krótsza od jednego kroku zostaje w akumulatorze i doliczy się
        w kolejnej klatce — czas nie ginie. Zaległość większa niż `max_steps`
        jest porzucana: nadrabianie jej kosztowałoby więcej niż jedna klatka,
        co wydłużyłoby następną klatkę i nakręciło spiralę śmierci.
        """
        self._accumulator += frame_dt
        count = int(self._accumulator / self.step)

        if count > self.max_steps:
            self._accumulator = 0.0
            return self.max_steps

        self._accumulator -= count * self.step
        return count
