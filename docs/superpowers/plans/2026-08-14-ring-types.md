# Typy okręgów — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Okręgi zyskują typy (kruchy, pancerny, dzielący się, boss), które różnicują wytrzymałość, tempo zwężania, wypłatę i wygląd, a ich skład na planszy przesuwa się wraz z falą.

**Architecture:** Typ jest **danymi**, nie klasą — `RingType` to zamrożony dataclass z mnożnikami, a `RING_TYPES` to tabela w stylu istniejących `UPGRADES` / `ACHIEVEMENTS`. `CircleRing` czyta liczby ze swojego typu. Zachowanie, którego nie da się sprowadzić do liczby (podział na mniejsze okręgi), wykonuje `RingField`, bo to on jest właścicielem stawiania okręgów — okrąg nigdy nie sięga do pola.

**Tech Stack:** Python 3.14, pygame-ce 2.5.7, pytest 9. Interpreter: `./.venv/Scripts/python.exe`.

**Spec:** `docs/superpowers/specs/2026-08-14-ring-types-design.md`

## Global Constraints

- **Identyfikatory po angielsku, komentarze i docstringi po polsku.** Tak jest w całym repo.
- **Warstwa logiki nie może wymagać okna pygame.** Wszystkie 46 istniejących testów działa bez `pygame.init()`; nowe też muszą.
- **Bez polskich znaków diakrytycznych w tekstach rysowanych na ekranie** (`notifications.add`, etykiety). Reszta kodu i komentarze — normalna polszczyzna.
- **TDD bez wyjątków:** test przed implementacją, obejrzeć czerwień, dopiero potem kod.
- **Jedno zadanie = jeden commit.** Format: `feat: ...` / `fix: ...` / `docs: ...`, treść po angielsku.
- **`config.ball_damage` wynosi 1 i nic go nie zmienia** — dlatego pancerz idzie przez mnożnik HP, nigdy przez odporność procentową.
- Uruchamianie testów: `./.venv/Scripts/python.exe -m pytest -q`
- Smoke test gry: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py` (oczekiwany kod wyjścia 124).

---

### Task 1: Tabela typów okręgów

**Files:**
- Create: `ring_types.py`
- Test: `tests/test_ring_types.py`

**Interfaces:**
- Consumes: nic (moduł samodzielny, importuje tylko `random` i `dataclasses`).
- Produces:
  - `RingType` — zamrożony dataclass, pola: `id: str`, `name: str`, `color: tuple[int,int,int]`, `hp_multiplier: float`, `shrink_multiplier: float`, `coin_multiplier: float`, `splits_into: int`, `thickness: int`, `unlock_wave: int`, `weight: float`, `weight_per_wave: float`
  - `RingType.effective_weight(wave: int) -> float`
  - Stałe typów: `NORMAL`, `FRAGILE`, `ARMORED`, `SPLITTING`, `BOSS`
  - `RING_TYPES: list[RingType]`, `SPAWNABLE_TYPES: list[RingType]`
  - `pick_type(wave: int, rng: random.Random) -> RingType`
  - `BOSS_EVERY: int = 10`

- [ ] **Step 1: Write the failing tests**

Utwórz `tests/test_ring_types.py`:

```python
import random

from ring_types import (
    ARMORED,
    BOSS,
    FRAGILE,
    NORMAL,
    SPAWNABLE_TYPES,
    SPLITTING,
    pick_type,
)


def test_weight_is_zero_before_unlock_wave():
    """Typ niedostępny na danej fali nie może w ogóle wypaść."""
    assert ARMORED.effective_weight(3) == 0.0


def test_weight_equals_base_on_unlock_wave():
    assert ARMORED.effective_weight(4) == 1.0


def test_weight_grows_with_wave_for_special_types():
    assert ARMORED.effective_weight(20) == 1.0 + 0.25 * 16


def test_normal_weight_shrinks_with_wave():
    """Zwykły okrąg ustępuje miejsca specjalnym w miarę postępu."""
    assert NORMAL.effective_weight(20) < NORMAL.effective_weight(1)


def test_normal_weight_reaches_zero_around_wave_30():
    """Od tej fali plansza składa się wyłącznie z typów specjalnych."""
    assert NORMAL.effective_weight(29) > 0.0
    assert NORMAL.effective_weight(30) == 0.0


def test_boss_is_not_in_the_random_pool():
    """Boss stawiany jest deterministycznie, nie losowany."""
    assert BOSS not in SPAWNABLE_TYPES


def test_only_normal_can_appear_on_wave_one():
    rng = random.Random(1234)

    picked = {pick_type(1, rng).id for _ in range(200)}

    assert picked == {"normal"}


def test_wave_twenty_draws_all_unlocked_types():
    rng = random.Random(1234)

    picked = {pick_type(20, rng).id for _ in range(500)}

    assert picked == {"normal", "fragile", "armored", "splitting"}


def test_armored_is_the_most_common_type_on_wave_twenty():
    """Krzywa trudności: pancerny ma na fali 20 największą wagę (39%)."""
    rng = random.Random(1234)

    counts: dict[str, int] = {}
    for _ in range(5000):
        ring_type = pick_type(20, rng)
        counts[ring_type.id] = counts.get(ring_type.id, 0) + 1

    assert max(counts, key=counts.get) == "armored"


def test_fragile_pays_more_and_dies_faster_than_normal():
    assert FRAGILE.hp_multiplier < NORMAL.hp_multiplier
    assert FRAGILE.coin_multiplier > NORMAL.coin_multiplier


def test_splitting_ring_declares_two_children():
    assert SPLITTING.splits_into == 2


def test_boss_shrinks_slower_to_leave_time_for_the_fight():
    assert BOSS.shrink_multiplier < 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_types.py -q`
Expected: błąd kolekcji `ModuleNotFoundError: No module named 'ring_types'`.

- [ ] **Step 3: Write the implementation**

Utwórz `ring_types.py`:

```python
import random
from dataclasses import dataclass

# Co ile fal pojawia się boss.
BOSS_EVERY: int = 10


@dataclass(frozen=True)
class RingType:
    """Wariant okręgu opisany liczbami, nie zachowaniem.

    Zamrożony, bo typ jest współdzielony przez wszystkie okręgi danego rodzaju —
    przypadkowa zmiana pola przestawiłaby balans dla całej planszy naraz.
    """

    id: str
    name: str                              # etykieta na planszy, pusta = bez etykiety
    color: tuple[int, int, int]
    hp_multiplier: float = 1.0             # względem state.get_ring_hp()
    shrink_multiplier: float = 1.0
    coin_multiplier: float = 1.0
    splits_into: int = 0                   # ile mniejszych okręgów po śmierci
    thickness: int = 4
    unlock_wave: int = 1
    weight: float = 0.0                    # waga losowania na fali odblokowania
    weight_per_wave: float = 0.0           # przyrost wagi za każdą kolejną falę

    def effective_weight(self, wave: int) -> float:
        """Waga losowania na danej fali — całą krzywą trudności robią te dwie liczby."""
        if wave < self.unlock_wave:
            return 0.0
        return max(0.0, self.weight + self.weight_per_wave * (wave - self.unlock_wave))


NORMAL = RingType(
    "normal", "", (60, 120, 200),
    unlock_wave=1, weight=10.0, weight_per_wave=-0.35,
)
FRAGILE = RingType(
    "fragile", "kruchy", (240, 200, 60),
    hp_multiplier=0.15, coin_multiplier=3.0,
    unlock_wave=2, weight=2.0,
)
ARMORED = RingType(
    "armored", "pancerny", (150, 155, 170),
    hp_multiplier=3.0, coin_multiplier=2.5, thickness=6,
    unlock_wave=4, weight=1.0, weight_per_wave=0.25,
)
SPLITTING = RingType(
    "splitting", "dzielacy sie", (170, 90, 200),
    hp_multiplier=0.6, coin_multiplier=0.6, splits_into=2,
    unlock_wave=6, weight=0.5, weight_per_wave=0.15,
)
BOSS = RingType(
    "boss", "BOSS", (220, 70, 70),
    hp_multiplier=4.0, shrink_multiplier=0.5, coin_multiplier=8.0, thickness=8,
    unlock_wave=BOSS_EVERY, weight=0.0,
)

RING_TYPES: list[RingType] = [NORMAL, FRAGILE, ARMORED, SPLITTING, BOSS]

# Boss stawiany jest deterministycznie co BOSS_EVERY fal, więc nie bierze
# udziału w losowaniu ważonym.
SPAWNABLE_TYPES: list[RingType] = [t for t in RING_TYPES if t is not BOSS]


def pick_type(wave: int, rng: random.Random) -> RingType:
    """Losuje typ okręgu ważony falą.

    `rng` jest wstrzykiwany, bo rozkład typów to jedyna część systemu, w której
    błąd strojenia jest niewidoczny gołym okiem — z ustalonym ziarnem da się go
    sprawdzić testem.
    """
    weights = [t.effective_weight(wave) for t in SPAWNABLE_TYPES]
    if sum(weights) <= 0.0:
        return NORMAL
    return rng.choices(SPAWNABLE_TYPES, weights=weights, k=1)[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_types.py -q`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add ring_types.py tests/test_ring_types.py
git commit -m "feat: add ring type table with wave-weighted spawn selection"
```

---

### Task 2: `CircleRing` przyjmuje typ

**Files:**
- Modify: `circle_ring.py:8-31` (`__init__`), `circle_ring.py:48-55` (`_update_color`), `circle_ring.py:57-67` (`update`)
- Test: `tests/test_circle_ring_types.py`

**Interfaces:**
- Consumes: `ring_types.NORMAL`, `ring_types.ARMORED`, `ring_types.FRAGILE`, `ring_types.BOSS`, `RingType` (Task 1)
- Produces:
  - `CircleRing.__init__(config, window_size, hp=100, ring_type=NORMAL)`
  - `CircleRing.type: RingType` — typ okręgu
  - `CircleRing.split_resolved: bool` — czy podział po śmierci został już rozliczony (używa Task 6)

- [ ] **Step 1: Write the failing tests**

Utwórz `tests/test_circle_ring_types.py`:

```python
from circle_ring import CircleRing
from config import Config
from ring_types import ARMORED, BOSS, FRAGILE, NORMAL


def test_default_ring_is_normal():
    ring = CircleRing(Config(), (400, 400), hp=100)

    assert ring.type is NORMAL


def test_armored_ring_gets_three_times_the_hp():
    """Pancerz idzie przez HP, bo ball_damage wynosi 1 i mnożnik obrażeń
    po zaokrągleniu w górę nic by nie zmienił."""
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ARMORED)

    assert ring.max_hp == 300
    assert ring.hp == 300


def test_fragile_ring_gets_a_fraction_of_the_hp():
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=FRAGILE)

    assert ring.max_hp == 15


def test_ring_hp_is_never_below_one():
    """Okrąg z zerowym HP byłby martwy w chwili postawienia."""
    ring = CircleRing(Config(), (400, 400), hp=1, ring_type=FRAGILE)

    assert ring.max_hp >= 1


def test_ring_takes_its_colour_and_thickness_from_the_type():
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=BOSS)

    assert ring.base_color == BOSS.color
    assert ring.thickness == BOSS.thickness


def test_full_health_ring_is_drawn_in_its_type_colour():
    """Interpolacja ku czerwieni musi startować z koloru typu, nie ze stałej."""
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ARMORED)

    ring._update_color()

    assert ring.color == ARMORED.color


def test_damaged_ring_shifts_towards_red():
    ring = CircleRing(Config(), (400, 400), hp=100, ring_type=ARMORED)
    ring.hp = ring.max_hp // 2

    ring._update_color()

    assert ring.color[0] > ARMORED.color[0]


def test_boss_shrinks_at_half_speed():
    config = Config()
    config.ring_shrink_speed = 100.0
    normal = CircleRing(config, (400, 400), hp=100)
    boss = CircleRing(config, (400, 400), hp=100, ring_type=BOSS)
    start = normal.radius

    normal.update(1.0)
    boss.update(1.0)

    assert start - normal.radius == 100.0
    assert start - boss.radius == 50.0


def test_new_ring_has_no_split_resolved_yet():
    ring = CircleRing(Config(), (400, 400), hp=100)

    assert ring.split_resolved is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_circle_ring_types.py -q`
Expected: `TypeError: CircleRing.__init__() got an unexpected keyword argument 'ring_type'` oraz `AttributeError: 'CircleRing' object has no attribute 'type'`.

- [ ] **Step 3: Write the implementation**

W `circle_ring.py` dodaj import na górze pliku, pod istniejące `from config import Config`:

```python
from ring_types import NORMAL, RingType
```

Podmień początek `__init__` (obecne linie 8-19):

```python
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
```

Podmień `_update_color` (obecne linie 48-55):

```python
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
```

W `update` podmień linię zwężania:

```python
        # Zmniejszanie — współczynnik prędkości (np. 0.05 gdy ice aktywny)
        self.radius -= (self.config.ring_shrink_speed * speed_multiplier
                        * self.type.shrink_multiplier * dt)
```

- [ ] **Step 4: Run all tests**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: `67 passed` (46 dotychczasowych + 12 z Task 1 + 9 z Task 2 — jeśli któryś stary test padnie, to regresja do naprawienia teraz).

- [ ] **Step 5: Commit**

```bash
git add circle_ring.py tests/test_circle_ring_types.py
git commit -m "feat: rings carry a type driving hp, colour, thickness and shrink rate"
```

---

### Task 3: `RingField` stawia okręgi z typem

**Files:**
- Modify: `ring_field.py` (cały plik — sygnatury `__init__`, `spawn`, `update`, `clear`)
- Modify: `main.py:100` (konstrukcja pola), `main.py:128`, `main.py:215`, `main.py:231` (wywołania `clear`), `main.py:297` (wywołanie `update`)
- Test: `tests/test_ring_field.py` (dopisanie testów)

**Interfaces:**
- Consumes: `pick_type(wave, rng)`, `NORMAL` (Task 1); `CircleRing(..., ring_type=...)` (Task 2)
- Produces:
  - `RingField.__init__(config, size, hp, wave=1, rng=None)`
  - `RingField.spawn(hp: int, wave: int) -> CircleRing`
  - `RingField.update(dt: float, hp: int, wave: int, speed_multiplier: float = 1.0) -> None`
  - `RingField.clear(hp: int, wave: int) -> None`

- [ ] **Step 1: Write the failing tests**

Dopisz na końcu `tests/test_ring_field.py`:

```python
def test_field_spawns_typed_rings():
    import random

    from ring_types import NORMAL

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=1,
                      rng=random.Random(7))

    assert field.rings[0].type is NORMAL


def test_field_passes_base_hp_through_to_the_ring():
    """Na fali 1 dostępny jest wyłącznie typ zwykły (mnożnik 1.0),
    więc HP okręgu musi być równe HP bazowemu."""
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=1,
                      rng=random.Random(7))

    assert field.rings[0].max_hp == 100


def test_field_uses_the_injected_rng():
    """Dwa pola z tym samym ziarnem muszą postawić tę samą sekwencję typów."""
    import random

    config_a = Config()
    field_a = RingField(config_a, (400, 400), hp=100, wave=20,
                        rng=random.Random(99))
    config_a.ring_spawn_interval = 0.5
    config_a.ring_shrink_speed = 60.0

    config_b = Config()
    field_b = RingField(config_b, (400, 400), hp=100, wave=20,
                        rng=random.Random(99))
    config_b.ring_spawn_interval = 0.5
    config_b.ring_shrink_speed = 60.0

    for _ in range(2000):
        field_a.update(1 / 240, hp=100, wave=20)
        field_b.update(1 / 240, hp=100, wave=20)

    assert ([r.type.id for r in field_a.rings]
            == [r.type.id for r in field_b.rings])


def test_high_wave_field_contains_special_rings():
    """Na fali 20 pole nie może składać się z samych zwykłych okręgów."""
    import random

    config = Config()
    config.ring_spawn_interval = 0.5
    config.ring_shrink_speed = 60.0
    field = RingField(config, (400, 400), hp=100, wave=20,
                      rng=random.Random(5))

    seen: set[str] = set()
    for _ in range(4000):
        field.update(1 / 240, hp=100, wave=20)
        seen.update(r.type.id for r in field.rings)

    assert seen - {"normal"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py -q`
Expected: `TypeError: RingField.__init__() got an unexpected keyword argument 'wave'`

- [ ] **Step 3: Write the implementation**

W `ring_field.py` dodaj importy na górze:

```python
import random

from circle_ring import CircleRing
from config import Config
from ring_types import pick_type
```

Podmień `__init__`:

```python
    def __init__(self, config: Config, size: tuple[int, int], hp: int,
                 wave: int = 1, rng: random.Random | None = None) -> None:
        self.config = config
        self.rings: list[CircleRing] = []
        self.spawn_timer: float = 0.0
        self._size = size
        self._rng = rng if rng is not None else random.Random()
        self.spawn(hp, wave)
```

Podmień `spawn`:

```python
    def spawn(self, hp: int, wave: int) -> CircleRing:
        """Stawia nowy okrąg na zewnętrznej krawędzi pola."""
        ring = CircleRing(self.config, self._size, hp=hp,
                          ring_type=pick_type(wave, self._rng))
        self.rings.append(ring)
        return ring
```

Podmień sygnaturę `update` i wszystkie wywołania `self.spawn` w środku:

```python
    def update(self, dt: float, hp: int, wave: int,
               speed_multiplier: float = 1.0) -> None:
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
                self.spawn(hp, wave)

        # Puste pole to gra bez celu
        if not self.alive():
            self.spawn(hp, wave)
```

Podmień `clear`:

```python
    def clear(self, hp: int, wave: int) -> None:
        """Czyści pole i stawia jeden świeży okrąg."""
        self.rings = []
        self.spawn_timer = 0.0
        self.spawn(hp, wave)
```

W `main.py` podmień pięć wywołań:

- linia 100: `field = RingField(config, (current_game_w, current_game_h), hp=state.get_ring_hp(), wave=state.wave)`
- linie 128, 215, 231: `field.clear(hp=state.get_ring_hp(), wave=state.wave)`
- linia 297: `field.update(dt, hp=state.get_ring_hp(), wave=state.wave, speed_multiplier=ice_mult)`
- linia 307 (wewnątrz obsługi zduszenia): `field.clear(hp=state.get_ring_hp(), wave=state.wave)`

- [ ] **Step 4: Run all tests and the smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: `71 passed`

Run: `cp save.json save.json.bak && SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py; echo "exit=$?"; cp save.json.bak save.json; rm -f save.json.bak`
Expected: `exit=124`

- [ ] **Step 5: Commit**

```bash
git add ring_field.py main.py tests/test_ring_field.py
git commit -m "feat: ring field spawns typed rings weighted by wave"
```

---

### Task 4: Wypłata zależna od typu

**Files:**
- Modify: `game_state.py:110-118` (`on_ring_destroyed`)
- Modify: `main.py:161` (bomba), `main.py:324` (kolizja piłki)
- Test: `tests/test_game_state.py` (dopisanie testów)

**Interfaces:**
- Consumes: `CircleRing.type` (Task 2)
- Produces: `GameState.on_ring_destroyed(gold_multiplier: float = 1.0, type_multiplier: float = 1.0) -> float`

- [ ] **Step 1: Write the failing tests**

Dopisz na końcu `tests/test_game_state.py`:

```python
def test_ring_payout_scales_with_type_multiplier():
    plain = GameState(wave=1)
    fancy = GameState(wave=1)

    base = plain.on_ring_destroyed()
    boosted = fancy.on_ring_destroyed(type_multiplier=2.5)

    assert boosted == base * 2.5


def test_gold_and_type_multipliers_stack():
    """Złoty power-up na pancernym ma dać 7 x 2.5, nie jedno z dwóch."""
    plain = GameState(wave=1)
    both = GameState(wave=1)

    base = plain.on_ring_destroyed()
    combined = both.on_ring_destroyed(gold_multiplier=7.0, type_multiplier=2.5)

    assert combined == base * 7.0 * 2.5


def test_type_multiplier_defaults_to_neutral():
    without = GameState(wave=3).on_ring_destroyed()
    explicit = GameState(wave=3).on_ring_destroyed(type_multiplier=1.0)

    assert without == explicit
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: `TypeError: GameState.on_ring_destroyed() got an unexpected keyword argument 'type_multiplier'`

- [ ] **Step 3: Write the implementation**

W `game_state.py` podmień `on_ring_destroyed`:

```python
    def on_ring_destroyed(self, gold_multiplier: float = 1.0,
                          type_multiplier: float = 1.0) -> float:
        """Wywołaj gdy okrąg zostanie zniszczony. Zwraca ile monet przyznano.

        Mnożniki działają niezależnie: złoty power-up na pancernym daje
        7 x 2.5, a nie większy z dwóch.
        """
        self.rings_destroyed += 1
        self.rings_destroyed_this_wave += 1
        base_coins = 10.0 + self.wave * 5.0
        explosion_bonus = 1.0 + self.upgrade_explosion * 0.3
        coins = base_coins * explosion_bonus * gold_multiplier * type_multiplier
        self.add_coins(coins)
        return coins
```

W `main.py` w obsłudze bomby (linia 161) podmień:

```python
                coins = state.on_ring_destroyed(
                    gold_multiplier=gold_mult,
                    type_multiplier=target.type.coin_multiplier)
```

W `main.py` w pętli kolizji (linia 324) podmień:

```python
                            coins = state.on_ring_destroyed(
                                gold_multiplier=gold_mult,
                                type_multiplier=ring.type.coin_multiplier)
```

- [ ] **Step 4: Run all tests**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: `74 passed`

- [ ] **Step 5: Commit**

```bash
git add game_state.py main.py tests/test_game_state.py
git commit -m "feat: ring payout scales with ring type"
```

---

### Task 5: Etykieta typu na planszy

**Files:**
- Modify: `circle_ring.py:187-...` (`draw`)
- Modify: `main.py:382-383` (pętla rysowania)
- Test: brak testu jednostkowego — warstwa rysowania wymaga powierzchni pygame; weryfikacja smoke testem

**Interfaces:**
- Consumes: `CircleRing.type.name` (Task 1, Task 2)
- Produces: `CircleRing.draw(surface: pygame.Surface, font: pygame.font.Font | None = None) -> None`

**Uwaga:** to jedyne zadanie w planie bez testu jednostkowego. Powód: `draw` rysuje na powierzchni pygame i nie zwraca nic, co dałoby się sprawdzić bez okna. Nie kombinuj z porównywaniem pikseli — weryfikacją jest smoke test i obejrzenie gry.

- [ ] **Step 1: Write the implementation**

W `circle_ring.py` podmień sygnaturę `draw` i dopisz etykietę na końcu metody, pod blokiem rysującym pasek HP:

```python
    def draw(self, surface: pygame.Surface,
             font: "pygame.font.Font | None" = None) -> None:
```

Na końcu `draw`, zaraz po bloku paska HP, dodaj:

```python
        # Etykieta typu pod paskiem HP — przy pięciu typach sam kolor
        # byłby zagadką. Zwykły okrąg ma pustą nazwę i nie dostaje etykiety.
        if self.alive and font is not None and self.type.name:
            label = font.render(self.type.name, True, self.base_color)
            surface.blit(label, label.get_rect(
                centerx=int(self.cx),
                top=int(self.cy + self.radius + 16)))
```

W `main.py` podmień pętlę rysowania (linie 382-383):

```python
        for ring in field.rings:
            ring.draw(screen, font)
```

- [ ] **Step 2: Run all tests**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: `74 passed` (bez zmian — to zadanie nie dodaje testów)

- [ ] **Step 3: Run the smoke test**

Run: `cp save.json save.json.bak && SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py; echo "exit=$?"; cp save.json.bak save.json; rm -f save.json.bak`
Expected: `exit=124`

- [ ] **Step 4: Commit**

```bash
git add circle_ring.py main.py
git commit -m "feat: label special ring types on the board"
```

---

### Task 6: Podział okręgu (B2b)

**Files:**
- Modify: `ring_field.py` (`update`, nowe metody `_resolve_splits` i `_split`)
- Test: `tests/test_ring_field.py` (dopisanie testów)

**Interfaces:**
- Consumes: `CircleRing.split_resolved` (Task 2), `SPLITTING`, `NORMAL` (Task 1), `RING_GAP` (istniejąca stała w `ring_field.py`)
- Produces: brak nowego publicznego API — podział dzieje się wewnątrz `RingField.update`

- [ ] **Step 1: Write the failing tests**

Dopisz na końcu `tests/test_ring_field.py`:

```python
def _splitting_ring(field, radius: float):
    """Podmienia jedyny okrąg pola na dzielący się o zadanym promieniu."""
    from ring_types import SPLITTING

    ring = field.rings[0]
    ring.type = SPLITTING
    ring.radius = radius
    return ring


def test_destroyed_splitting_ring_spawns_two_children():
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    assert len(field.alive()) == 2


def test_children_appear_inside_the_parent_one_gap_apart():
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    radii = sorted(r.radius for r in field.alive())
    assert radii == [220.0 - 2 * RING_GAP, 220.0 - RING_GAP]


def test_children_are_ordinary_rings():
    """Inaczej podział kaskadowałby w nieskończoność."""
    from ring_types import NORMAL

    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    assert all(r.type is NORMAL for r in field.alive())


def test_no_child_is_born_already_crushed():
    """Dziecko poniżej ring_min_radius natychmiast wywołałoby karę."""
    config, field = _field()
    config.ring_min_radius = 30.0
    ring = _splitting_ring(field, radius=100.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    assert all(r.radius > 30.0 for r in field.alive())


def test_splitting_ring_with_no_room_dies_without_children():
    config, field = _field()
    config.ring_min_radius = 30.0
    ring = _splitting_ring(field, radius=50.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)

    # Zostaje wyłącznie okrąg dostawiony regułą "puste pole to gra bez celu"
    assert all(r.radius == config.ring_start_radius for r in field.alive())


def test_split_happens_only_once():
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)
    ring.destroy()

    field.update(1 / 240, hp=100, wave=6)
    count_after_first = len(field.rings)
    field.update(1 / 240, hp=100, wave=6)

    assert len(field.rings) == count_after_first


def test_split_also_fires_for_rings_killed_outside_the_collision_loop():
    """Bomba woła ring.destroy() z zupełnie innego miejsca w main.py —
    podział musi zadziałać i wtedy."""
    _, field = _field()
    ring = _splitting_ring(field, radius=220.0)

    ring.destroy()          # dokładnie to, co robi power-up bomba
    field.update(1 / 240, hp=100, wave=6)

    assert len(field.alive()) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py -q`
Expected: 7 padających testów, pierwszy z `assert 1 == 2`.

- [ ] **Step 3: Write the implementation**

W `ring_field.py` dodaj import `NORMAL`:

```python
from ring_types import NORMAL, pick_type
```

Dodaj dwie metody do klasy `RingField`:

```python
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
```

W `update` wstaw wywołanie `_resolve_splits` **przed** usuwaniem wyblakłych okręgów:

```python
        for ring in self.rings:
            ring.update(dt, speed_multiplier=speed_multiplier)

        self._resolve_splits(hp)

        self.rings = [r for r in self.rings if not r.is_faded()]
```

- [ ] **Step 4: Run all tests and the smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: `81 passed`

Run: `cp save.json save.json.bak && SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py; echo "exit=$?"; cp save.json.bak save.json; rm -f save.json.bak`
Expected: `exit=124`

- [ ] **Step 5: Commit**

```bash
git add ring_field.py tests/test_ring_field.py
git commit -m "feat: splitting rings spawn smaller children when destroyed"
```

---

### Task 7: Boss co 10 fal (B2c)

**Files:**
- Modify: `ring_field.py` (`__init__`, nowa metoda `_next_type`, użycie w `spawn`)
- Test: `tests/test_ring_field.py` (dopisanie testów)

**Interfaces:**
- Consumes: `BOSS`, `BOSS_EVERY`, `pick_type` (Task 1)
- Produces: `RingField._next_type(wave: int) -> RingType` (prywatna, używana przez `spawn`)

- [ ] **Step 1: Write the failing tests**

Dopisz na końcu `tests/test_ring_field.py`:

```python
def test_boss_appears_on_every_tenth_wave():
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=10,
                      rng=random.Random(3))

    assert field.rings[0].type.id == "boss"


def test_no_boss_on_ordinary_waves():
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=9,
                      rng=random.Random(3))

    assert field.rings[0].type.id != "boss"


def test_only_one_boss_per_visit_to_a_boss_wave():
    import random

    config = Config()
    config.ring_spawn_interval = 0.1
    config.ring_shrink_speed = 60.0
    field = RingField(config, (400, 400), hp=100, wave=10,
                      rng=random.Random(3))

    for _ in range(2000):
        field.update(1 / 240, hp=100, wave=10)

    assert sum(1 for r in field.rings if r.type.id == "boss") <= 1


def test_boss_returns_after_losing_and_regaining_the_wave():
    """Zduszenie przez bossa cofa gracza na falę 9. Po powrocie na 10 boss
    musi czekać ponownie — inaczej gracz mijałby go bez walki na zawsze."""
    import random

    config = Config()
    field = RingField(config, (400, 400), hp=100, wave=10,
                      rng=random.Random(3))

    field.clear(hp=100, wave=9)     # kara za zduszenie
    field.clear(hp=100, wave=10)    # gracz odbudował falę

    assert field.rings[0].type.id == "boss"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py -q`
Expected: `test_boss_appears_on_every_tenth_wave` pada z `assert 'normal' == 'boss'`.

- [ ] **Step 3: Write the implementation**

W `ring_field.py` rozszerz import:

```python
from ring_types import BOSS, BOSS_EVERY, NORMAL, RingType, pick_type
```

W `__init__` dodaj dwa pola **przed** wywołaniem `self.spawn(hp, wave)`:

```python
        self._last_wave: int = wave
        self._boss_done_for_wave: int | None = None
```

Dodaj metodę:

```python
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
```

Podmień `spawn`, żeby korzystał z `_next_type`:

```python
    def spawn(self, hp: int, wave: int) -> CircleRing:
        """Stawia nowy okrąg na zewnętrznej krawędzi pola."""
        ring = CircleRing(self.config, self._size, hp=hp,
                          ring_type=self._next_type(wave))
        self.rings.append(ring)
        return ring
```

- [ ] **Step 4: Run all tests and the smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: `85 passed`

Run: `cp save.json save.json.bak && SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py; echo "exit=$?"; cp save.json.bak save.json; rm -f save.json.bak`
Expected: `exit=124`

- [ ] **Step 5: Commit**

```bash
git add ring_field.py tests/test_ring_field.py
git commit -m "feat: boss ring every tenth wave"
```

---

### Task 8: Pomiar strojenia

**Files:**
- Create: `tools/measure_ring_types.py`

**Interfaces:**
- Consumes: `RingField`, `Config`, `GameState`, `RING_TYPES` (Tasks 1-7)
- Produces: skrypt uruchamiany ręcznie, nic nie importuje go w grze

**Dlaczego to osobne zadanie:** przy limicie okręgów w kroku B1a jedenaście zielonych testów jednostkowych przepuściło błąd, przez który pole rosło do 60 okręgów. Testy sprawdzają pojedyncze reguły na krótkim odcinku; ten skrypt pokazuje, do czego reguły prowadzą po minutach gry. Rozkład ważony falą jest dokładnie tej samej natury.

- [ ] **Step 1: Write the script**

Utwórz `tools/measure_ring_types.py`:

```python
"""Pomiar strojenia typów okręgów — uruchamiany ręcznie, nie jest testem.

Testy jednostkowe sprawdzają, czy reguła działa. Ten skrypt pokazuje, do czego
reguła prowadzi po minutach gry: jaki procent spawnów to który typ i ile
okręgów utrzymuje się na planszy.

Uruchomienie:
    ./.venv/Scripts/python.exe tools/measure_ring_types.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config           # noqa: E402
from game_state import GameState    # noqa: E402
from ring_field import RingField    # noqa: E402

STEP = 1 / 240
SECONDS = 120


def measure(wave: int) -> None:
    config = Config()
    state = GameState(wave=wave)
    config.apply_upgrades(state)
    field = RingField(config, (700, 520), hp=state.get_ring_hp(),
                      wave=wave, rng=random.Random(42))

    seen: dict[str, int] = {}
    known: set[int] = set()
    counts: list[int] = []

    for _ in range(int(SECONDS / STEP)):
        field.update(STEP, hp=state.get_ring_hp(), wave=wave)
        for ring in field.rings:
            if id(ring) not in known:
                known.add(id(ring))
                seen[ring.type.id] = seen.get(ring.type.id, 0) + 1
        counts.append(len(field.alive()))

    total = sum(seen.values())
    shares = "  ".join(f"{name} {100 * n / total:.0f}%"
                       for name, n in sorted(seen.items()))
    print(f"fala {wave:>2}: spawnow {total:>3}  "
          f"max okr. {max(counts)}  sr. {sum(counts) / len(counts):.1f}")
    print(f"          {shares}")


if __name__ == "__main__":
    for wave in (1, 5, 10, 20, 30):
        measure(wave)
```

- [ ] **Step 2: Run the measurement**

Run: `./.venv/Scripts/python.exe tools/measure_ring_types.py`

Expected: raport dla fal 1/5/10/20/30. Sprawdź trzy rzeczy:
1. **Liczba okręgów nie przekracza 5** na żadnej fali (poza chwilowymi wyskokami po podziale).
2. **Udziały typów zgadzają się ze specem** (fala 10: ~55% zwykły, 16% kruchy, 20% pancerny, 9% dzielący się; fala 20: ~26/15/39/20). Odchylenie kilku punktów procentowych jest normalne przy tej liczbie próbek; różnica rzędu dziesiątek punktów oznacza błąd.
3. **Na fali 10 i 20 pojawia się dokładnie jeden boss.**

Jeśli któraś rzecz się nie zgadza, to błąd do naprawienia teraz — nie zapisuj rozbieżności jako „tak wyszło".

- [ ] **Step 3: Commit**

```bash
git add tools/measure_ring_types.py
git commit -m "chore: add ring type tuning measurement script"
```

---

## Uwaga do strojenia, do sprawdzenia w Task 8

Pancerny ma 3× HP. Na fali 1 zwykły okrąg ma 100 HP, a `config.ball_damage` wynosi 1, więc pancerny wymaga **300 odbić**. Przy tempie 2-3 odbić na sekundę to 100-150 sekund — dłużej, niż okrąg zdąży się zwęzić do minimum, czyli pancerny na niskich falach byłby praktycznie nie do zabicia inaczej niż przez dziurę.

Łagodzą to trzy rzeczy: pancerny odblokowuje się dopiero od fali 4, gracz ma wtedy zwykle ulepszenia dziur, a trafienie w dziurę zabija okrąg natychmiast niezależnie od HP.

Mimo to **zweryfikuj to pomiarem w Task 8**. Jeśli pancerne na falach 4-8 masowo dożywają zduszenia, obniż `hp_multiplier` z 3,0 do 2,0 w `ring_types.py` i powtórz pomiar. Ta zmiana należy do Task 8, nie do Task 1 — najpierw dane, potem korekta.
