import random

from circle_ring import CircleRing
from config import Config
from ring_types import BOSS, BOSS_EVERY, NORMAL, RingType, pick_type

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

    def __init__(self, config: Config, size: tuple[int, int], hp: int,
                 wave: int = 1, rng: random.Random | None = None) -> None:
        self.config = config
        self.rings: list[CircleRing] = []
        self.spawn_timer: float = 0.0
        self._size = size
        self._rng = rng if rng is not None else random.Random()
        self._last_wave: int = wave
        self._boss_done_for_wave: int | None = None
        self.spawn(hp, wave)

    def _next_type(self, wave: int) -> RingType:
        """Wybiera typ kolejnego okręgu — boss deterministycznie, reszta losowo.

        Znacznik bossa kasuje się przy każdej zmianie fali, w obie strony.
        Bez tego powstaje pułapka: boss dusi piłkę na fali 10, kara cofa gracza
        na 9, gracz odbudowuje 10 — a znacznik wciąż twierdzi, że boss dla fali
        10 już był, więc gracz mijałby go bez walki na zawsze.
        """
        if wave != self._last_wave:
            self._last_wave = wave
            self._boss_done_for_wave = None

        if wave % BOSS_EVERY == 0 and self._boss_done_for_wave != wave:
            self._boss_done_for_wave = wave
            return BOSS

        return pick_type(wave, self._rng)

    def spawn(self, hp: int, wave: int) -> CircleRing:
        """Stawia nowy okrąg na zewnętrznej krawędzi pola."""
        ring = CircleRing(self.config, self._size, hp=hp,
                          ring_type=self._next_type(wave))
        self.rings.append(ring)
        return ring

    def alive(self) -> list[CircleRing]:
        """Żywe okręgi od najbardziej wewnętrznego do zewnętrznego."""
        return sorted((r for r in self.rings if r.alive), key=lambda r: r.radius)

    def innermost(self) -> CircleRing | None:
        """Okrąg najbliższy piłce — jedyny, który może ją odbić."""
        alive = self.alive()
        return alive[0] if alive else None

    def is_crushed(self) -> bool:
        """Czy stos dociśnięto do minimum — piłka nie ma już gdzie grać."""
        inner = self.innermost()
        return inner is not None and inner.radius <= self.config.ring_min_radius

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

    def update(self, dt: float, hp: int, wave: int,
               speed_multiplier: float = 1.0) -> None:
        """Zwęża okręgi, sprząta wyblakłe i dostawia nowe co interwał."""
        for ring in self.rings:
            ring.update(dt, speed_multiplier=speed_multiplier)

        self._resolve_splits(hp)

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
                self.spawn(hp, wave)

        # Puste pole to gra bez celu
        if not self.alive():
            self.spawn(hp, wave)

    def _resolve_splits(self, hp: int) -> None:
        """Rozlicza okręgi, które zginęły od ostatniego wywołania.

        Pole robi to samo, zamiast czekać na sygnał z pętli głównej — dzięki
        temu podział działa także przy zabiciu bombą, która woła destroy()
        z zupełnie innego miejsca.
        """
        for ring in list(self.rings):
            if ring.alive or ring.split_resolved:
                continue
            ring.split_resolved = True
            self._split(ring, hp)

    def _split(self, parent: CircleRing, hp: int) -> None:
        """Stawia dzieci wewnątrz martwego rodzica, o RING_GAP od siebie.

        Dziecko musi zmieścić się powyżej ring_min_radius — poniżej urodziłoby
        się w stanie zduszenia i od razu ukarało gracza. Podział świadomie
        pomija limit ring_max_active: to jednorazowy wyskok, a limit pilnuje
        tempa spawnu, nie sufitu absolutnego.
        """
        for i in range(parent.type.splits_into):
            radius = parent.radius - RING_GAP * (i + 1)
            if radius <= self.config.ring_min_radius:
                break
            child = CircleRing(self.config, self._size, hp=hp,
                               ring_type=NORMAL)
            child.radius = radius
            child.cx = parent.cx
            child.cy = parent.cy
            self.rings.append(child)

    def clear(self, hp: int, wave: int) -> None:
        """Czyści pole i stawia jeden świeży okrąg."""
        self.rings = []
        self.spawn_timer = 0.0
        self.spawn(hp, wave)

    def recenter(self, size: tuple[int, int]) -> None:
        """Przenosi okręgi do środka planszy po zmianie rozmiaru okna."""
        self._size = size
        for ring in self.rings:
            ring.cx = size[0] / 2
            ring.cy = size[1] / 2
