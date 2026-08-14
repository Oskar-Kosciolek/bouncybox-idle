from circle_ring import CircleRing
from config import Config

# Minimalny odstęp promieni między sąsiednimi okręgami. Nie jest wymuszany
# na promieniach po fakcie — wynika z tego, kiedy wolno postawić nowy okrąg.
RING_GAP: float = 35.0


class RingField:
    """Utrzymuje pole współśrodkowych okręgów wokół środka planszy.

    Zbiera w jednym miejscu to, co wcześniej było rozsypane po pętli głównej:
    listę okręgów, odmierzanie spawnu, kolejność od środka i sprzątanie
    wyblakłych. Piłka jest wewnątrz stosu, więc dosięga tylko najbardziej
    wewnętrznego okręgu — stąd `alive()` zwraca je uporządkowane od środka.
    """

    def __init__(self, config: Config, size: tuple[int, int], hp: int) -> None:
        self.config = config
        self.rings: list[CircleRing] = []
        self.spawn_timer: float = 0.0
        self._size = size
        self.spawn(hp)

    def spawn(self, hp: int) -> CircleRing:
        """Stawia nowy okrąg na zewnętrznej krawędzi pola."""
        ring = CircleRing(self.config, self._size, hp=hp)
        self.rings.append(ring)
        return ring

    def alive(self) -> list[CircleRing]:
        """Żywe okręgi od najbardziej wewnętrznego do zewnętrznego."""
        return sorted((r for r in self.rings if r.alive), key=lambda r: r.radius)

    def innermost(self) -> CircleRing | None:
        """Okrąg najbliższy piłce — jedyny, który może ją odbić."""
        alive = self.alive()
        return alive[0] if alive else None

    def has_room(self) -> bool:
        """Czy jest miejsce na kolejny okrąg.

        Dwa warunki, bo sam odstęp przy krawędzi nie wystarcza: przy szybkim
        zwężaniu zewnętrzny okrąg schodzi z krawędzi niemal natychmiast i pole
        rosłoby bez końca. Stąd twardy limit `ring_max_active`.
        """
        alive = self.alive()
        if not alive:
            return True
        if len(alive) >= self.config.ring_max_active:
            return False
        return alive[-1].radius <= self.config.ring_start_radius - RING_GAP

    def update(self, dt: float, hp: int, speed_multiplier: float = 1.0) -> None:
        """Zwęża okręgi, sprząta wyblakłe i dostawia nowe co interwał."""
        for ring in self.rings:
            ring.update(dt, speed_multiplier=speed_multiplier)

        self.rings = [r for r in self.rings if not r.is_faded()]

        # Żaden okrąg nie schodzi poniżej minimum — inaczej zwinąłby się do
        # zera i zniknął bez udziału gracza.
        for ring in self.rings:
            if ring.alive and ring.radius < self.config.ring_min_radius:
                ring.radius = self.config.ring_min_radius

        self.spawn_timer += dt
        if self.spawn_timer >= self.config.ring_spawn_interval:
            self.spawn_timer = 0.0
            if self.has_room():
                self.spawn(hp)

        # Puste pole to gra bez celu
        if not self.alive():
            self.spawn(hp)

    def clear(self, hp: int) -> None:
        """Czyści pole i stawia jeden świeży okrąg."""
        self.rings = []
        self.spawn_timer = 0.0
        self.spawn(hp)

    def recenter(self, size: tuple[int, int]) -> None:
        """Przenosi okręgi do środka planszy po zmianie rozmiaru okna."""
        self._size = size
        for ring in self.rings:
            ring.cx = size[0] / 2
            ring.cy = size[1] / 2
