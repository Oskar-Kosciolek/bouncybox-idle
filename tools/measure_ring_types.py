"""Pomiar strojenia typów okręgów — uruchamiany ręcznie, nie jest testem.

Testy jednostkowe sprawdzają, czy reguła działa. Ten skrypt pokazuje, do czego
reguła prowadzi po minutach gry: jaki procent spawnów to który typ, jak długo
każdy typ żyje i jak często stos dusi piłkę.

Piłka jest tu przybliżona, nie symulowana. Odbija się od najbardziej
wewnętrznego okręgu, a między odbiciami przelatuje przez jego wnętrze, więc
częstotliwość odbić to mniej więcej `predkosc / (2 * promien)` na sekundę.
Każde odbicie zadaje `config.ball_damage` obrażeń. To wystarcza, żeby okręgi
ginęły w realistycznym tempie — a bez ginących okręgów pole zapełnia się do
limitu i przestaje spawnować, przez co rozkład typów w ogóle się nie ujawnia.

Uruchomienie:
    ./.venv/Scripts/python.exe tools/measure_ring_types.py
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config           # noqa: E402
from game_state import GameState    # noqa: E402
from ring_field import RingField    # noqa: E402

STEP = 1 / 240
SECONDS = 300


def measure(wave: int) -> None:
    config = Config()
    state = GameState(wave=wave)
    config.apply_upgrades(state)
    field = RingField(config, (700, 520), hp=state.get_ring_hp(),
                      wave=wave, rng=random.Random(42))

    ball_speed = math.hypot(config.initial_speed_x, config.initial_speed_y)

    spawned: dict[str, int] = {}
    lifetimes: dict[str, list[float]] = {}
    born_at: dict[int, float] = {}
    # Trzymamy referencje do okręgów, nie same id — CPython używa id ponownie
    # po zwolnieniu obiektu, więc po wyczyszczeniu pola nowe okręgi
    # dostawały id starych i nie były liczone jako spawny.
    known: set[int] = set()
    keep_alive: list = []
    counts: list[int] = []
    crushes = 0
    damage_debt = 0.0
    now = 0.0

    for _ in range(int(SECONDS / STEP)):
        now += STEP
        field.update(STEP, hp=state.get_ring_hp(), wave=wave)

        for ring in field.rings:
            if id(ring) not in known:
                known.add(id(ring))
                keep_alive.append(ring)
                born_at[id(ring)] = now
                spawned[ring.type.id] = spawned.get(ring.type.id, 0) + 1

        # Przybliżona piłka: odbicia od najbardziej wewnętrznego okręgu
        inner = field.innermost()
        if inner is not None:
            bounces_per_second = ball_speed / max(1.0, 2.0 * inner.radius)
            damage_debt += bounces_per_second * config.ball_damage * STEP
            while damage_debt >= 1.0:
                damage_debt -= 1.0
                if inner.hit(config.ball_damage):
                    lifetimes.setdefault(inner.type.id, []).append(
                        now - born_at[id(inner)])
                    break

        if field.is_crushed():
            crushes += 1
            state.on_crushed()
            config.apply_upgrades(state)
            field.clear(hp=state.get_ring_hp(), wave=wave)

        counts.append(len(field.alive()))

    total = sum(spawned.values())
    print(f"fala {wave:>2}: spawnow {total:>3}   max okr. {max(counts)}   "
          f"sr. {sum(counts) / len(counts):.1f}   zduszen {crushes}")
    for name in sorted(spawned):
        times = lifetimes.get(name, [])
        avg = f"{sum(times) / len(times):.1f} s" if times else "nie zginal"
        print(f"          {name:<9} {100 * spawned[name] / total:>3.0f}%   "
              f"zabitych {len(times):>3}   sr. zycie {avg}")


if __name__ == "__main__":
    for wave in (1, 5, 10, 20, 30):
        measure(wave)
