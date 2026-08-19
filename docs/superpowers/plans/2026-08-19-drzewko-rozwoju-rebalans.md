# Drzewko rozwoju — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drzewko rozwoju przestaje kończyć się po 30 minutach — dostaje warstwy odblokowywane falą 10 i 25, gałęzie bez sufitu jako ujście monet, koszty liczone w minutach gry zamiast stałych, oraz prestiż nagradzający za osiągniętą falę.

**Architecture:** Koszt przestaje być stałą, a staje się `cost_minutes` mnożone przez zmierzony przychód na fali odblokowania (`INCOME_AT_UNLOCK`) — trzy liczby zamiast dwudziestu pięciu. Licznik fali rozszczepia się na trzy pola o rozłącznych zadaniach: `wave` (trudność, spada przy zduszeniu), `run_max_wave` (szczyt runu → kryształy, zeruje przy prestiżu), `max_wave_reached` (szczyt kiedykolwiek → bramki warstw, nie zeruje nigdy). Wszystkie obrażenia przechodzą przez nowe `RingField.apply_damage()`, bo krytyk, przebicie i fala uderzeniowa to trzy ulepszenia, ale jeden moment w grze — a dwa z nich potrzebują następnego okręgu, którego `CircleRing` z definicji nie widzi.

**Tech Stack:** Python 3.14, pygame-ce 2.5.7, pytest. Interpreter: `./.venv/Scripts/python.exe`.

**Spec:** `docs/superpowers/specs/2026-08-19-drzewko-rozwoju-rebalans-design.md`

## Global Constraints

- **Commity robi człowiek.** Agent NIE woła `git commit` ani `git add`. Ostatni krok każdego zadania podaje gotową krótką wiadomość do skopiowania.
- **Identyfikatory po angielsku, komentarze i docstringi po polsku.** Tak jest w całym repo.
- **Bez polskich znaków diakrytycznych w tekstach rysowanych na ekranie** (`notifications.add`, etykiety w `ui/`). Reszta kodu i komentarze — normalna polszczyzna.
- **Warstwa logiki nie może wymagać okna pygame.** Wszystkie 178 istniejących testów działa bez `pygame.init()`; nowe też muszą.
- **TDD bez wyjątków:** test przed implementacją, obejrzeć czerwień, dopiero potem kod.
- **Baza to 178 przechodzących testów w 0,81 s.** Po każdym zadaniu cały zestaw musi być zielony.
- **Kotwice kosztu:** `INCOME_AT_UNLOCK = {1: 150.0, 10: 15_000.0, 25: 90_000.0}`
- **Warstwy:** `unlock_wave` przyjmuje wyłącznie 1, 10 albo 25.
- **Krzywa kryształów:** `PRESTIGE_MIN_WAVE = 10`, `CRYSTAL_SCALE = 3.0`, `CRYSTAL_EXPONENT = 1.5`
- **`coins_on_bounce`:** 1% wypłaty za okrąg na poziom (`BOUNCE_PAYOUT_FRACTION = 0.01`).
- Uruchamianie testów: `./.venv/Scripts/python.exe -m pytest -q`
- Smoke test gry: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py` (oczekiwany kod wyjścia 124).

---

# ETAP 1 — model kosztu i bramki

Po tym etapie warstwa 1 jest przestrojona, bramki falowe działają, a warstwy 2 i 3 są jeszcze puste. Nic nie dotyka fizyki, więc ryzyko regresji jest minimalne.

---

### Task 1: Koszt liczony w minutach gry

**Files:**
- Modify: `upgrade_tree.py:1-60` (dataclass `Upgrade`), `upgrade_tree.py:95-118` (tabela `UPGRADES`)
- Test: `tests/test_upgrade_tree.py`

**Interfaces:**
- Consumes: nic.
- Produces:
  - `INCOME_AT_UNLOCK: dict[int, float]` — `{1: 150.0, 10: 15_000.0, 25: 90_000.0}`
  - `Upgrade.cost_minutes: float` — zastępuje pole `base_cost`
  - `Upgrade.unlock_wave: int = 1`
  - `Upgrade.base_cost` — teraz `@property`, zwraca `cost_minutes * INCOME_AT_UNLOCK[unlock_wave]`
  - `Upgrade.cost_at_level(current_level: int) -> float` — sygnatura bez zmian
  - `_validate_unlock_waves()` — walidacja przy imporcie modułu

- [ ] **Step 1: Write the failing tests**

Dopisz do `tests/test_upgrade_tree.py`:

```python
import pytest

from upgrade_tree import INCOME_AT_UNLOCK, UPGRADES, Upgrade


def test_base_cost_is_minutes_times_anchor():
    """Koszt pierwszego poziomu to deklarowane minuty gry razy kotwica warstwy."""
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=2.0, unlock_wave=10)
    assert upg.base_cost == 2.0 * INCOME_AT_UNLOCK[10]


def test_base_cost_differs_per_tier_for_same_minutes():
    """Te same minuty na wyzszej warstwie kosztuja wiecej monet."""
    tier1 = Upgrade("a", "A", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=1)
    tier3 = Upgrade("b", "B", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=25)
    assert tier3.base_cost > tier1.base_cost * 100


def test_cost_at_level_still_compounds():
    upg = Upgrade("x", "X", "opis", "ball", 5, cost_minutes=1.0,
                  unlock_wave=1, cost_multiplier=2.0)
    assert upg.cost_at_level(0) == 150.0
    assert upg.cost_at_level(3) == 150.0 * 8


def test_every_upgrade_uses_a_known_tier():
    """Bramka falowa musi miec kotwice — inaczej base_cost rzuci KeyError w grze."""
    for upg in UPGRADES:
        assert upg.unlock_wave in INCOME_AT_UNLOCK


def test_unknown_unlock_wave_fails_at_validation():
    from upgrade_tree import _validate_unlock_waves
    bad = [Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=15)]
    with pytest.raises(ValueError, match="unlock_wave"):
        _validate_unlock_waves(bad)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_upgrade_tree.py -q`
Expected: FAIL — `ImportError: cannot import name 'INCOME_AT_UNLOCK'`

- [ ] **Step 3: Add the anchor table and validation**

W `upgrade_tree.py`, nad dataclassem `Upgrade`:

```python
# Zmierzony przychód na minutę w momencie, w którym gracz faktycznie kupuje
# daną warstwę: warstwę 1 podczas bootstrapu, warstwę 2 koło fali 10,
# warstwę 3 koło fali 25. Kotwica jest przychodem, nie wypłatą za okrąg —
# od fali 10 gracz zbiera ~430 okręgów na minutę i ta liczba się wypłaszcza,
# ale między falą 1 a 10 podwaja się, więc sama wypłata zaniżyłaby warstwę 1
# dwukrotnie względem reszty drzewka.
INCOME_AT_UNLOCK: dict[int, float] = {1: 150.0, 10: 15_000.0, 25: 90_000.0}


def _validate_unlock_waves(upgrades: list["Upgrade"]) -> None:
    """Sprawdza, że każda warstwa ma kotwicę kosztu.

    Wołane przy imporcie modułu, nie przy pierwszym zakupie — ulepszenie
    z nieznaną falą odblokowania rzuciłoby KeyError dopiero wtedy, gdy gracz
    kliknie węzeł, czyli po godzinie gry.
    """
    for upg in upgrades:
        if upg.unlock_wave not in INCOME_AT_UNLOCK:
            raise ValueError(
                f"{upg.id}: unlock_wave={upg.unlock_wave} nie ma kotwicy "
                f"w INCOME_AT_UNLOCK (dozwolone: {sorted(INCOME_AT_UNLOCK)})")
```

- [ ] **Step 4: Swap base_cost for cost_minutes**

W dataclassie `Upgrade` zamień pole `base_cost: float` na:

```python
    cost_minutes: float   # ile minut gry ma kosztować pierwszy poziom
    cost_multiplier: float = 2.0
    requires: Optional[str] = None
    unlock_wave: int = 1   # warstwa: 1, 10 albo 25
```

i dodaj property tuż nad `cost_at_level`:

```python
    @property
    def base_cost(self) -> float:
        """Koszt pierwszego poziomu w monetach.

        Liczony, nie wpisany: stała w kodzie nie wie nic o ekonomii, która
        rośnie wykładniczo z falą, więc rozjeżdżała się przy każdej zmianie
        wypłaty. Minuta gry znaczy to samo na fali 1 i na fali 25.
        """
        return self.cost_minutes * INCOME_AT_UNLOCK[self.unlock_wave]
```

- [ ] **Step 5: Convert the existing table to minutes**

Zamień tabelę `UPGRADES` (koszty podzielone przez 150 — to ta sama cena w monetach, tylko wyrażona w minutach):

```python
UPGRADES: list[Upgrade] = [
    # Gałąź: Piłka
    Upgrade("ball_speed",  "Predkosc pilki", "+20% predkosci",             "ball", 5, 0.333),
    Upgrade("ball_size",   "Rozmiar pilki",  "Wieksza pilka = latwiej",    "ball", 3, 0.533, requires="ball_speed"),
    Upgrade("multi_ball",  "Multi-ball",     "Dodatkowa pilka na planszy", "ball", 3, 2.0,   requires="ball_speed"),
    Upgrade("ball_trail",  "Smuga",          "Efekt wizualny smugi",       "ball", 1, 1.0,   requires="ball_speed"),
    Upgrade("ball_damage", "Sila uderzenia", "+25% obrazen za poziom",     "ball", None, 1.333,
            cost_multiplier=1.6, requires="ball_speed"),

    # Gałąź: Okręgi
    Upgrade("hole_size",  "Rozmiar dziury", "+10 stopni rozmiaru dziury", "rings", 5, 0.4),
    Upgrade("hole_count", "Liczba dziur",   "+1 dziura w okregu",         "rings", 3, 0.8,   requires="hole_size"),
    Upgrade("hole_speed", "Ruch dziury",    "Dziury sie obracaja",        "rings", 3, 0.667, requires="hole_size"),
    Upgrade("explosion",  "Eksplozja",      "+monety za zniszczenie",     "rings", 3, 0.533),

    # Gałąź: Ekonomia
    Upgrade("coin_multiplier", "Mnoznik monet",     "+50% monet za okrag",  "economy", 5, 0.667),
    Upgrade("auto_collector",  "Auto-kolektor",     "Monety same wpadaja",  "economy", 1, 3.333, requires="coin_multiplier"),
    Upgrade("coins_on_bounce", "Monety za odbicie", "+1% wyplaty za odbicie", "economy", 3, 1.0, requires="coin_multiplier"),
]

_validate_unlock_waves(UPGRADES)
```

Uwaga: `multi_ball` dostaje `max_level=3` (było 2) — zgodnie ze spec.

- [ ] **Step 6: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 183 testy

- [ ] **Step 7: Commit (człowiek)**

```
feat: express upgrade costs in minutes of play
```

---

### Task 2: Trzy pola fali

**Files:**
- Modify: `game_state.py:30-45` (pola), `game_state.py:200-216` (`check_wave_progress`), `game_state.py:105-150` (`prestige`)
- Test: `tests/test_game_state.py`

**Interfaces:**
- Consumes: nic.
- Produces:
  - `GameState.run_max_wave: int = 1` — szczyt tego runu, zeruje przy prestiżu
  - `GameState.max_wave_reached: int = 1` — szczyt kiedykolwiek, nie zeruje nigdy
  - `check_wave_progress()` podbija oba (sygnatura bez zmian, zwraca `bool`)

- [ ] **Step 1: Write the failing tests**

Dopisz do `tests/test_game_state.py`:

```python
def test_wave_progress_raises_both_peaks():
    st = GameState(rings_to_next_wave=1)
    st.rings_destroyed_this_wave = 1
    assert st.check_wave_progress() is True
    assert st.wave == 2
    assert st.run_max_wave == 2
    assert st.max_wave_reached == 2


def test_crush_lowers_wave_but_no_peak():
    """Zduszenie cofa trudnosc, nie dorobek — inaczej gracz traci dostep do warstw."""
    st = GameState(wave=12, run_max_wave=12, max_wave_reached=12)
    st.on_crushed()
    assert st.wave == 11
    assert st.run_max_wave == 12
    assert st.max_wave_reached == 12


def test_prestige_resets_run_peak_but_not_lifetime_peak():
    """Run peak zasila krysztaly, wiec musi zerowac; lifetime peak trzyma bramki warstw."""
    st = GameState(wave=30, run_max_wave=30, max_wave_reached=30)
    assert st.prestige() is True
    assert st.wave == 1
    assert st.run_max_wave == 1
    assert st.max_wave_reached == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: FAIL — `TypeError: unexpected keyword argument 'run_max_wave'`

- [ ] **Step 3: Add the two fields**

W `GameState`, tuż pod `wave: int = 1`:

```python
    # Szczyt fali w tym runie. Osobne pole od `wave`, bo `wave` spada przy
    # zduszeniu, a kryształy za prestiż mają płacić za to, co gracz osiągnął,
    # nie za to, na czym akurat stoi.
    run_max_wave: int = 1
    # Szczyt fali kiedykolwiek. Osobne pole od `run_max_wave`, bo bramki warstw
    # nie mogą zerować się przy prestiżu — gracz straciłby dostęp do treści,
    # którą już odkrył. Zakupy resetują, odkryta treść zostaje.
    max_wave_reached: int = 1
```

- [ ] **Step 4: Raise both peaks on wave-up**

W `check_wave_progress()`, po `self.wave += 1`:

```python
            self.wave += 1
            self.run_max_wave = max(self.run_max_wave, self.wave)
            self.max_wave_reached = max(self.max_wave_reached, self.wave)
```

- [ ] **Step 5: Preserve the lifetime peak across prestige**

W `prestige()` dopisz do zestawu zachowywanych pól — obok `saved_prestige_count`:

```python
        saved_max_wave_reached = self.max_wave_reached
```

i po resecie, obok pozostałych przywróceń:

```python
        self.max_wave_reached = saved_max_wave_reached
```

`run_max_wave` celowo NIE jest przywracane — reset do domyślnej jedynki jest jego zadaniem.

- [ ] **Step 6: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 186 testów

- [ ] **Step 7: Commit (człowiek)**

```
feat: split wave counter into run peak and lifetime peak
```

---

### Task 3: Bramka falowa w drzewku

**Files:**
- Modify: `upgrade_tree.py:44-48` (`is_unlocked`)
- Test: `tests/test_upgrade_tree.py`

**Interfaces:**
- Consumes: `Upgrade.unlock_wave` (Task 1), `GameState.max_wave_reached` (Task 2).
- Produces: `Upgrade.is_unlocked(state) -> bool` — sygnatura bez zmian, dochodzi warunek falowy.

- [ ] **Step 1: Write the failing tests**

```python
from game_state import GameState
from upgrade_tree import Upgrade


def test_tier_two_locked_below_unlock_wave():
    st = GameState(max_wave_reached=9)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=10)
    assert upg.is_unlocked(st) is False


def test_tier_two_unlocks_at_wave():
    st = GameState(max_wave_reached=10)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=10)
    assert upg.is_unlocked(st) is True


def test_tier_stays_unlocked_after_being_crushed():
    """Zduszenie cofa fale — ulepszenie nie moze przez to zniknac z drzewka."""
    st = GameState(wave=10, run_max_wave=10, max_wave_reached=10)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=10)
    st.on_crushed()
    assert st.wave == 9
    assert upg.is_unlocked(st) is True


def test_tier_stays_unlocked_after_prestige():
    st = GameState(wave=30, run_max_wave=30, max_wave_reached=30)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=25)
    st.prestige()
    assert upg.is_unlocked(st) is True


def test_wave_gate_and_requires_both_apply():
    st = GameState(max_wave_reached=10)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0,
                  unlock_wave=10, requires="ball_speed")
    assert upg.is_unlocked(st) is False
    st.upgrade_ball_speed = 1
    assert upg.is_unlocked(st) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_upgrade_tree.py -q`
Expected: FAIL — `test_tier_two_locked_below_unlock_wave` zwraca `True`

- [ ] **Step 3: Add the wave condition**

Zamień `is_unlocked` w `upgrade_tree.py`:

```python
    def is_unlocked(self, state) -> bool:
        """Sprawdza, czy warstwa i wymaganie (requires) są spełnione.

        Bramka patrzy na `max_wave_reached`, nie na `wave` — `on_crushed()`
        cofa falę o jeden, więc na `wave` ulepszenie z warstwy 2 znikałoby
        graczowi po jednym zduszeniu razem z kupionymi poziomami.
        """
        if state.max_wave_reached < self.unlock_wave:
            return False
        if self.requires is None:
            return True
        return getattr(state, f"upgrade_{self.requires}") > 0
```

- [ ] **Step 4: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 191 testów

- [ ] **Step 5: Commit (człowiek)**

```
feat: gate upgrades behind wave tiers
```

---

### Task 4: Migracja starego zapisu

**Files:**
- Modify: `save_manager.py:47-70` (`load_game`)
- Test: `tests/test_save_manager.py`

**Interfaces:**
- Consumes: `GameState.run_max_wave`, `GameState.max_wave_reached` (Task 2).
- Produces: `load_game(path) -> GameState | None` — sygnatura bez zmian.

- [ ] **Step 1: Write the failing tests**

```python
import json

from save_manager import load_game


def test_old_save_without_peaks_gets_them_from_wave(tmp_path):
    """Domyslne 1 zablokowaloby warstwy graczowi, ktory byl juz na fali 30."""
    path = tmp_path / "save.json"
    path.write_text(json.dumps({"version": 1, "wave": 30, "coins": 5.0}),
                    encoding="utf-8")
    st = load_game(path)
    assert st.max_wave_reached == 30
    assert st.run_max_wave == 30


def test_new_save_keeps_its_own_peaks(tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({"version": 1, "wave": 5,
                                "run_max_wave": 7, "max_wave_reached": 41}),
                    encoding="utf-8")
    st = load_game(path)
    assert st.run_max_wave == 7
    assert st.max_wave_reached == 41
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_save_manager.py -q`
Expected: FAIL — `assert 1 == 30`

- [ ] **Step 3: Migrate on load**

W `load_game`, po zbudowaniu słownika `known`, przed `return GameState(**known)`:

```python
        # Migracja: zapisy sprzed warstw nie mają szczytów fali, a domyślna
        # jedynka jest tu błędem, nie pustką — zablokowałaby warstwy graczowi,
        # który dawno przekroczył falę 25. Falę z zapisu traktujemy jako szczyt.
        wave = known.get("wave", 1)
        known.setdefault("max_wave_reached", wave)
        known.setdefault("run_max_wave", wave)
```

- [ ] **Step 4: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 193 testy

- [ ] **Step 5: Commit (człowiek)**

```
fix: seed wave peaks from wave when loading old saves
```

---

### Task 5: Monety za odbicie skalowane falą

**Files:**
- Modify: `game_state.py:95-100` (`on_bounce`)
- Test: `tests/test_game_state.py`

**Interfaces:**
- Consumes: `GameState.ring_payout()` (istnieje).
- Produces:
  - `BOUNCE_PAYOUT_FRACTION: float = 0.01`
  - `GameState.on_bounce()` — sygnatura bez zmian

- [ ] **Step 1: Write the failing tests**

```python
from game_state import BOUNCE_PAYOUT_FRACTION, GameState


def test_bounce_pays_fraction_of_ring_payout():
    st = GameState(upgrade_coins_on_bounce=1)
    st.on_bounce()
    assert st.coins == st.ring_payout() * BOUNCE_PAYOUT_FRACTION


def test_bounce_income_grows_with_wave():
    """Stale 0.5 mnozylo przychod fali 1 przez 35 i bylo martwe na fali 25."""
    early = GameState(wave=1, upgrade_coins_on_bounce=3)
    late = GameState(wave=25, upgrade_coins_on_bounce=3)
    early.on_bounce()
    late.on_bounce()
    assert late.coins > early.coins * 10


def test_bounce_pays_nothing_without_the_upgrade():
    st = GameState()
    st.on_bounce()
    assert st.coins == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: FAIL — `ImportError: cannot import name 'BOUNCE_PAYOUT_FRACTION'`

- [ ] **Step 3: Replace the flat rate**

W `game_state.py`, obok pozostałych stałych ekonomii:

```python
# Ułamek wypłaty za okrąg, jaki płaci jedno odbicie na poziom ulepszenia.
# Stała 0,5 monety płaciła od odbić, a odbicia zależą od prędkości piłki
# i liczby piłek — rzeczy kupowanych raz. Efekt: mnożnik 35x na fali 1
# (90/min → 3,2K/min) i zero znaczenia od fali 25. Ułamek wypłaty skaluje się
# z falą, więc ulepszenie znaczy tyle samo przez cały run.
BOUNCE_PAYOUT_FRACTION: float = 0.01
```

i `on_bounce`:

```python
    def on_bounce(self) -> None:
        """Wywołaj przy każdym odbiciu jeśli upgrade_coins_on_bounce > 0."""
        if self.upgrade_coins_on_bounce > 0:
            self.add_coins(self.ring_payout() * BOUNCE_PAYOUT_FRACTION
                           * self.upgrade_coins_on_bounce)
```

- [ ] **Step 4: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 196 testów. Jeśli któryś stary test zakłada 0,5 monety za odbicie — popraw go, to zmiana zamierzona.

- [ ] **Step 5: Commit (człowiek)**

```
fix: scale bounce income with ring payout
```

---

### Task 6: Węzeł zablokowany falą w drzewku

**Files:**
- Modify: `ui/tree_view.py:178-215` (`_draw_node`), `ui/tree_view.py:239-270` (`_draw_detail`)
- Test: `tests/test_tree_view.py`

**Interfaces:**
- Consumes: `Upgrade.unlock_wave` (Task 1), `Upgrade.is_unlocked` (Task 3).
- Produces: `TreeView.lock_label(upg) -> str` — pusty string, gdy odblokowane; inaczej `"od fali N"` albo `"wymaga: <id>"`.

- [ ] **Step 1: Write the failing tests**

```python
from game_state import GameState
from ui.tree_view import TreeView
from upgrade_tree import Upgrade


def _view(state):
    """TreeView przyjmuje (state, upgrades) — bez prostokąta, ten liczy się
    dopiero przy rysowaniu w _set_rect."""
    return TreeView(state, [])


def test_no_label_when_unlocked():
    st = GameState(max_wave_reached=10)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=10)
    assert _view(st).lock_label(upg) == ""


def test_wave_lock_names_the_wave():
    st = GameState(max_wave_reached=4)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0, unlock_wave=10)
    assert _view(st).lock_label(upg) == "od fali 10"


def test_wave_lock_wins_over_requires():
    """Gracz ma najpierw dojechac do fali — wymaganie pokazujemy dopiero potem."""
    st = GameState(max_wave_reached=4)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0,
                  unlock_wave=10, requires="ball_speed")
    assert _view(st).lock_label(upg) == "od fali 10"


def test_requires_label_when_wave_is_met():
    st = GameState(max_wave_reached=10)
    upg = Upgrade("x", "X", "opis", "ball", 3, cost_minutes=1.0,
                  unlock_wave=10, requires="ball_speed")
    assert _view(st).lock_label(upg) == "wymaga: ball_speed"
```


- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_tree_view.py -q`
Expected: FAIL — `AttributeError: 'TreeView' object has no attribute 'lock_label'`

- [ ] **Step 3: Implement the label**

W `TreeView`, obok pozostałych metod pomocniczych:

```python
    def lock_label(self, upg: "Upgrade") -> str:
        """Powód blokady węzła, gotowy do narysowania. Pusty = odblokowane.

        Fala ma pierwszeństwo przed `requires`, bo jest warunkiem, którego
        gracz nie może spełnić zakupem — pokazanie mu najpierw wymagania
        kazałoby kupić coś, co i tak niczego nie odblokuje.
        """
        if upg.is_unlocked(self.state):
            return ""
        if self.state.max_wave_reached < upg.unlock_wave:
            return f"od fali {upg.unlock_wave}"
        return f"wymaga: {upg.requires}"
```

- [ ] **Step 4: Draw it**

W `_draw_node`, w gałęzi `if not unlocked:` — po narysowaniu koła dopisz etykietę pod węzłem:

```python
        label = self.lock_label(upg)
        if label:
            lock_surf = font.render(label, True, (130, 130, 150))
            surface.blit(lock_surf,
                         lock_surf.get_rect(center=(cx, cy + _NODE_R + 10)))
```

- [ ] **Step 5: Run the full suite and smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 200 testów

Run: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py`
Expected: kod wyjścia 124 (timeout, czyli gra wystartowała i działała)

- [ ] **Step 6: Commit (człowiek)**

```
feat: show wave lock reason on tree nodes
```

---

# ETAP 2 — przepływ obrażeń

**Etap najwyższego ryzyka** — dotyka kodu kolizji, który już raz miał błędy ze swept i cooldownami. Zadania 7-9 są celowo **bez zmiany zachowania**: przebudowują przepływ, nie mechanikę. Mechaniki dochodzą dopiero na zielonych testach w zadaniach 10-13.

---

### Task 7: HitResult zamiast bool

**Files:**
- Modify: `circle_ring.py:1-30` (importy, nowy dataclass), `circle_ring.py:124-198` (`check_collision`)
- Test: `tests/test_collision.py`

**Interfaces:**
- Consumes: nic.
- Produces:
  - `HitResult` — zamrożony dataclass: `bounced: bool = False`, `through_hole: bool = False`, `crit: bool = False`, `damage: float = 0.0`, `destroyed: tuple["CircleRing", ...] = ()`
  - `HitResult.__bool__() -> bool` — `bounced or through_hole`
  - `CircleRing.check_collision(ball) -> HitResult` (było `bool`)

- [ ] **Step 1: Write the failing tests**

```python
from circle_ring import HitResult


def test_empty_result_is_falsy():
    """Pozwala zostawic `if ring.check_collision(ball):` w kodzie wolajacym."""
    assert not HitResult()


def test_bounce_result_is_truthy():
    assert HitResult(bounced=True)


def test_hole_result_is_truthy_but_not_a_bounce():
    """Dziura to zdarzenie, ale nie odbicie — petla glowna musi je rozroznic."""
    res = HitResult(through_hole=True)
    assert res
    assert res.bounced is False


def test_destroyed_defaults_to_empty_tuple():
    """Krotka od pierwszej linijki, zeby zalozenie 'jeden trup na kolizje'
    nie wrocilo, gdy fala uderzeniowa zacznie zabijac dwa okregi."""
    assert HitResult().destroyed == ()
```

Oraz test zachowania — kolizja nadal działa jak dziś. `tests/test_collision.py`
ma już `_board()` zwracające `(config, CircleRing(config, (400, 400)))`; dopisz
obok dwie funkcje pomocnicze, z których korzystają też zadania 9 i 13:

```python
from ball import Ball


def _ring():
    """Sam okrąg, bez piłki — do testów geometrii łuków."""
    config = Config()
    return CircleRing(config, (400, 400))


def _ring_and_ball():
    """Okrąg i piłka postawiona dokładnie na jego ściance, lecąca na zewnątrz.

    Piłka startuje wewnątrz i dostaje prędkość radialną, bo `check_collision`
    rozpoznaje stronę nadlotu po `ball.prev_x/prev_y` — piłka postawiona
    bez historii ruchu bywa klasyfikowana jako nadlatująca z zewnątrz.
    """
    ring = _ring()
    ball = Ball(ring.cx + ring.radius - 2, ring.cy, 200.0, 0.0)
    ball.prev_x, ball.prev_y = ring.cx, ring.cy
    return ring, ball


def test_check_collision_reports_a_bounce():
    ring, ball = _ring_and_ball()
    res = ring.check_collision(ball)
    assert res.bounced is True
    assert res.damage > 0
```

Sprawdź w `ball.py:1-30` faktyczną sygnaturę `Ball.__init__` i dopasuj
wywołanie — reszta testów w tym pliku pokazuje działający wzorzec.

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_collision.py -q`
Expected: FAIL — `ImportError: cannot import name 'HitResult'`

- [ ] **Step 3: Add the dataclass**

W `circle_ring.py`, nad klasą `CircleRing`:

```python
@dataclass(frozen=True)
class HitResult:
    """Co się stało przy jednym kontakcie piłki z okręgiem.

    Zastępuje bool, bo pętla główna musiała odróżniać dziurę od pudła przez
    porównanie HP sprzed i po kolizji — a po dodaniu fali uderzeniowej jedno
    trafienie może zabić dwa okręgi i ta rekonstrukcja przestaje być możliwa.
    """
    bounced: bool = False
    through_hole: bool = False
    crit: bool = False
    damage: float = 0.0
    destroyed: tuple["CircleRing", ...] = ()

    def __bool__(self) -> bool:
        """Prawda, gdy cokolwiek się wydarzyło — pudło jest fałszywe."""
        return self.bounced or self.through_hole
```

- [ ] **Step 4: Return it from check_collision**

W `check_collision` zamień wszystkie `return False` / `return True` (linie 141, 154, 166, 169, 198) na:

- brak kolizji → `return HitResult()`
- przelot przez dziurę → `return HitResult(through_hole=True, damage=hole_damage)` gdzie `hole_damage = self.config.ball_damage * self.config.hole_damage_multiplier`
- cooldown → `return HitResult()`
- odbicie → `return HitResult(bounced=True, damage=self.config.ball_damage)`

Zmień też adnotację: `def check_collision(self, ball) -> HitResult:`

- [ ] **Step 5: Fix the call site**

W `main.py:368` zamień:

```python
                        collided = ring.check_collision(ball)
```

na:

```python
                        hit = ring.check_collision(ball)
                        collided = hit.bounced
```

Reszta pętli zostaje bez zmian — to zadanie nie zmienia zachowania.

- [ ] **Step 6: Run the full suite and smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 205 testów

Run: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py`
Expected: kod wyjścia 124

- [ ] **Step 7: Commit (człowiek)**

```
refactor: return HitResult from check_collision
```

---

### Task 8: RingField.apply_damage

**Files:**
- Modify: `ring_field.py:1-30` (importy), nowa metoda w `RingField`
- Test: `tests/test_ring_field.py`

**Interfaces:**
- Consumes: `HitResult` (Task 7), `RingField.alive()` (istnieje, sortuje rosnąco po promieniu), `RingField._rng` (istnieje, prywatne pole ustawiane w `__init__`).
- Produces:
  - `RingField.apply_damage(ring, amount: float, propagate: bool = True) -> HitResult`
  - `RingField.next_outward(ring) -> CircleRing | None`

- [ ] **Step 1: Write the failing tests**

Repo nie używa fixtur pytest, tylko funkcji pomocniczych z podkreśleniem (`_field()`, `_board()`). Trzymaj się tego. Dopisz do `tests/test_ring_field.py`:

```python
import random

from circle_ring import CircleRing
from config import Config
from ring_field import RingField


def _field_with(count: int, hp: int = 100, seed: int = 1):
    """Pole z dokładnie `count` okręgami o rosnących promieniach.

    Stawiamy je wprost, zamiast czekać na spawn — test ma sprawdzać
    obrażenia, nie harmonogram spawnu.
    """
    config = Config()
    field = RingField(config, (400, 400), hp=hp, rng=random.Random(seed))
    field.rings = []
    for i in range(count):
        ring = CircleRing(config, (200, 200), hp=hp)
        ring.radius = 60.0 + 40.0 * i
        field.rings.append(ring)
    return field


def test_apply_damage_reduces_hp():
    field = _field_with(1)
    ring = field.alive()[0]
    before = ring.hp
    field.apply_damage(ring, 10)
    assert ring.hp == before - 10


def test_apply_damage_reports_the_kill():
    field = _field_with(1)
    ring = field.alive()[0]
    res = field.apply_damage(ring, ring.hp)
    assert res.destroyed == (ring,)


def test_apply_damage_reports_nothing_when_ring_survives():
    field = _field_with(1)
    ring = field.alive()[0]
    res = field.apply_damage(ring, 1)
    assert res.destroyed == ()


def test_next_outward_is_the_bigger_neighbour():
    field = _field_with(2)
    inner, outer = field.alive()
    assert field.next_outward(inner) is outer
    assert field.next_outward(outer) is None
```

Sprawdź w `circle_ring.py:15-30`, jak dokładnie wygląda sygnatura `CircleRing.__init__` (pozycja `hp`, `ring_type`), i dopasuj wywołanie w `_field_with`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py -q`
Expected: FAIL — `AttributeError: 'RingField' object has no attribute 'apply_damage'`

- [ ] **Step 3: Implement both methods**

W `ring_field.py`:

```python
    def next_outward(self, ring: CircleRing) -> CircleRing | None:
        """Sąsiad okręgu od strony zewnętrznej, albo None dla najdalszego.

        `alive()` sortuje rosnąco po promieniu, więc „następny na zewnątrz"
        to po prostu kolejny element listy.
        """
        living = self.alive()
        try:
            idx = living.index(ring)
        except ValueError:
            return None
        return living[idx + 1] if idx + 1 < len(living) else None

    def apply_damage(self, ring: CircleRing, amount: float,
                     propagate: bool = True) -> HitResult:
        """Zadaje obrażenia okręgowi wraz ze wszystkim, co się z nimi niesie.

        Krytyk, przebicie i fala uderzeniowa to trzy ulepszenia, ale jeden
        moment w grze. Trzymanie ich tutaj, a nie w CircleRing, zostawia
        okręgowi geometrię, a polu — oddziaływania między okręgami, których
        pojedynczy okrąg z definicji nie widzi. Sam wymóg danych (przebicie
        i fala potrzebują NASTĘPNEGO okręgu) wskazuje tę warstwę.

        propagate=False dla wywołań wtórnych: fala uderzeniowa propaguje
        dokładnie o jeden krok, inaczej okrąg zabity falą wywołałby własną
        i powstałaby kaskada przez całą planszę.
        """
        killed: list[CircleRing] = []
        if ring.hit(int(round(amount))):
            killed.append(ring)
        return HitResult(damage=amount, destroyed=tuple(killed))
```

Dodaj import `from circle_ring import CircleRing, HitResult` (jeśli `CircleRing` jest już importowany, dopisz tylko `HitResult`).

- [ ] **Step 4: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 209 testów

- [ ] **Step 5: Commit (człowiek)**

```
feat: add RingField.apply_damage as the single damage path
```

---

### Task 9: Pętla główna konsumuje HitResult

**Files:**
- Modify: `circle_ring.py:124-198` (`check_collision` przestaje zadawać obrażenia), `main.py:363-425`
- Test: `tests/test_collision.py`

**Interfaces:**
- Consumes: `HitResult` (Task 7), `RingField.apply_damage` (Task 8).
- Produces: `CircleRing.check_collision(ball) -> HitResult` — zwraca **zamiar** obrażeń w `damage`, sam ich nie zadaje.

- [ ] **Step 1: Write the failing test**

```python
def test_check_collision_no_longer_deals_damage():
    simple_ring, ball_at_wall = _ring_and_ball()
    """Okrag opisuje trafienie; obrazenia zadaje pole, bo tylko ono widzi sasiadow."""
    before = simple_ring.hp
    res = simple_ring.check_collision(ball_at_wall)
    assert res.bounced is True
    assert res.damage > 0
    assert simple_ring.hp == before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_collision.py -q`
Expected: FAIL — HP spadło mimo braku `apply_damage`

- [ ] **Step 3: Strip damage from check_collision**

W `circle_ring.py` usuń oba wywołania `self.hit(...)` z `check_collision` (linia 161 — dziura, linia 197 — odbicie). Wartość obrażeń trafia wyłącznie do `HitResult.damage`. `ball.hole_cooldown = HOLE_HIT_COOLDOWN` zostaje na miejscu — to stan piłki, nie okręgu.

- [ ] **Step 4: Rewire the main loop**

W `main.py` zamień blok kolizji (od `hit = ring.check_collision(ball)`):

```python
                        hit = ring.check_collision(ball)
                        if not hit:
                            continue
                        result = field.apply_damage(ring, hit.damage)
                        if hit.bounced:
                            audio.bounce(ring.radius, config.ring_min_radius,
                                         config.ring_start_radius, now=game_time)
                        else:
                            audio.hole_hit()

                        for dead in result.destroyed:
                            audio.ring_destroyed()
                            gold_mult = getattr(dead, "gold_multiplier", 1.0)
                            coins = state.on_ring_destroyed(
                                gold_multiplier=gold_mult,
                                type_multiplier=dead.type.coin_multiplier)
                            particles.explode_ring(dead.cx, dead.cy,
                                                   dead.radius, dead.color)
                            label = "Dziura!" if hit.through_hole else "Zniszczony!"
                            colour = (255, 220, 50) if hit.through_hole else (100, 200, 255)
                            notifications.add(f"{label} +{short_number(coins)} monet",
                                              color=colour)
                            floating_texts.add(dead.cx, dead.cy,
                                               f"+{short_number(coins)}",
                                               color=(255, 220, 50), lifetime=1.2)
                            if state.check_wave_progress():
                                config.apply_upgrades(state)
                                for b in balls:
                                    b.radius = config.ball_radius
                            newly_unlocked = check_achievements(state)
                            _notify_achievements(newly_unlocked, notifications, audio)

                        if hit.bounced:
                            floating_texts.add(
                                ball.x + random.randint(-10, 10),
                                ball.y + random.randint(-15, -5),
                                f"-{int(result.damage)}",
                                color=(255, 180, 80), lifetime=0.7)
                            state.on_bounce()
                            break
```

Pętla `for dead in result.destroyed:` zastępuje warunek `if was_alive and not ring.alive:`. Usuń niepotrzebne już `was_alive` i `hp_before`.

- [ ] **Step 5: Run the full suite and smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 210 testów

Run: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py`
Expected: kod wyjścia 124

Zagraj chwilę ręcznie (`./.venv/Scripts/python.exe main.py`) i sprawdź, że dźwięki, powiadomienia i monety zachowują się jak przed zmianą.

- [ ] **Step 6: Commit (człowiek)**

```
refactor: route all ring damage through RingField
```

---

### Task 10: Trafienie krytyczne

**Files:**
- Modify: `game_state.py` (pole), `upgrade_tree.py` (wpis), `config.py` (`apply_upgrades`), `ring_field.py` (`apply_damage`)
- Test: `tests/test_ring_field.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `RingField.apply_damage` (Task 8).
- Produces:
  - `GameState.upgrade_crit_chance: int = 0`
  - `Config.crit_chance: float` — 0.0-1.0
  - `Config.crit_multiplier: float` — startowo 3.0
  - `HitResult.crit` wypełniane przez `apply_damage`

- [ ] **Step 1: Write the failing tests**

```python
def test_crit_multiplies_damage():
    field = _field_with(1, hp=1000)
    field.config.crit_chance = 1.0      # zawsze krytyk
    field.config.crit_multiplier = 3.0
    ring = field.alive()[0]
    before = ring.hp
    res = field.apply_damage(ring, 10)
    assert res.crit is True
    assert before - ring.hp == 30


def test_no_crit_when_chance_is_zero():
    field = _field_with(1, hp=1000)
    field.config.crit_chance = 0.0
    ring = field.alive()[0]
    res = field.apply_damage(ring, 10)
    assert res.crit is False


def test_crit_uses_the_injected_rng():
    """Ustalone ziarno = powtarzalny wynik; inaczej krytyka nie da sie testowac.

    Pole trzyma generator w prywatnym `_rng`, wiec ziarno podajemy przy
    budowie pola, a nie przez podmiane atrybutu.
    """
    def rolls(seed):
        field = _field_with(1, hp=10_000_000, seed=seed)
        field.config.crit_chance = 0.5
        ring = field.alive()[0]
        return [field.apply_damage(ring, 1).crit for _ in range(20)]

    assert rolls(7) == rolls(7)
    assert rolls(7) != rolls(8)
```

oraz w `tests/test_config.py`:

```python
def test_crit_chance_grows_with_upgrade():
    cfg, st = Config(), GameState(upgrade_crit_chance=3)
    cfg.apply_upgrades(st)
    assert cfg.crit_chance == pytest.approx(0.15)


def test_crit_chance_is_zero_without_upgrade():
    cfg, st = Config(), GameState()
    cfg.apply_upgrades(st)
    assert cfg.crit_chance == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py tests/test_config.py -q`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'crit_chance'`

- [ ] **Step 3: Add state field and upgrade entry**

`game_state.py`, w gałęzi Piłka:

```python
    upgrade_crit_chance: int = 0      # warstwa 2, max 5
```

`upgrade_tree.py`, na końcu gałęzi `ball`:

```python
    Upgrade("crit_chance", "Trafienie krytyczne", "+5% szansy na potrojne obrazenia",
            "ball", 5, 0.7, unlock_wave=10, requires="ball_damage"),
```

- [ ] **Step 4: Derive the config fields**

`config.py`, pola bazowe:

```python
BASE_CRIT_MULTIPLIER: float = 3.0
CRIT_CHANCE_PER_LEVEL: float = 0.05
```

w dataclassie `Config`:

```python
    crit_chance: float = 0.0
    crit_multiplier: float = BASE_CRIT_MULTIPLIER
```

w `apply_upgrades`:

```python
        self.crit_chance = state.upgrade_crit_chance * CRIT_CHANCE_PER_LEVEL
        self.crit_multiplier = BASE_CRIT_MULTIPLIER
```

- [ ] **Step 5: Roll the crit in apply_damage**

W `RingField.apply_damage`, na początku:

```python
        crit = (self.config.crit_chance > 0.0
                and self._rng.random() < self.config.crit_chance)
        if crit:
            amount *= self.config.crit_multiplier
```

i przekaż `crit=crit` do `HitResult`.

- [ ] **Step 6: Write the failing test for crit power**

`Siła krytyka` to warstwa 3 i osobny węzeł, ale ten sam mnożnik w `Config`, więc dokładamy go tutaj, a nie w oddzielnym zadaniu.

W `tests/test_config.py`:

```python
def test_crit_power_raises_the_multiplier():
    cfg, st = Config(), GameState(upgrade_crit_power=2)
    cfg.apply_upgrades(st)
    assert cfg.crit_multiplier == 5.0      # 3.0 bazowe + 2 x 1.0


def test_crit_multiplier_is_three_without_the_upgrade():
    cfg, st = Config(), GameState()
    cfg.apply_upgrades(st)
    assert cfg.crit_multiplier == 3.0
```

W `tests/test_upgrade_tree.py`:

```python
def test_crit_power_is_an_uncapped_tier_three_entry():
    upg = next(u for u in UPGRADES if u.id == "crit_power")
    assert upg.unlock_wave == 25
    assert upg.max_level is None
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_upgrade_tree.py -q`
Expected: FAIL — `TypeError: unexpected keyword argument 'upgrade_crit_power'`

- [ ] **Step 8: Implement crit power**

`game_state.py`, gałąź Piłka:

```python
    upgrade_crit_power: int = 0       # warstwa 3, bez sufitu
```

`upgrade_tree.py`, gałąź `ball`:

```python
    Upgrade("crit_power", "Sila krytyka", "+1 do mnoznika krytycznego",
            "ball", None, 2.5, cost_multiplier=1.8, unlock_wave=25,
            requires="crit_chance"),
```

`config.py`:

```python
CRIT_POWER_PER_LEVEL: float = 1.0
```

i w `apply_upgrades` zamień stałą linię mnożnika na:

```python
        # Rośnie mnożnik, nie szansa — szansa ma sufit na 100%, a ujście
        # monet w warstwie 3 nie może się kończyć.
        self.crit_multiplier = (BASE_CRIT_MULTIPLIER
                                + state.upgrade_crit_power * CRIT_POWER_PER_LEVEL)
```

- [ ] **Step 9: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 218 testów

- [ ] **Step 10: Commit (człowiek)**

```
feat: add crit chance and crit power upgrades
```

---

### Task 11: Fala uderzeniowa

**Files:**
- Modify: `game_state.py`, `upgrade_tree.py`, `config.py`, `ring_field.py`
- Test: `tests/test_ring_field.py`

**Interfaces:**
- Consumes: `RingField.apply_damage`, `RingField.next_outward` (Task 8).
- Produces:
  - `GameState.upgrade_shockwave: int = 0`
  - `Config.shockwave_fraction: float` — ułamek maks. HP zabitego okręgu

- [ ] **Step 1: Write the failing tests**

```python
def test_shockwave_hits_the_next_ring_outward():
    field = _field_with(2, hp=1000)
    field.config.shockwave_fraction = 0.15
    inner, outer = field.alive()
    outer_before = outer.hp
    field.apply_damage(inner, inner.hp)          # zabija wewnetrzny
    assert outer.hp == outer_before - int(round(inner.max_hp * 0.15))


def test_shockwave_does_nothing_when_ring_survives():
    field = _field_with(2, hp=1000)
    field.config.shockwave_fraction = 0.15
    inner, outer = field.alive()
    outer_before = outer.hp
    field.apply_damage(inner, 1)
    assert outer.hp == outer_before


def test_shockwave_does_not_cascade():
    """Okrag zabity fala nie wywoluje wlasnej — inaczej jedno trafienie
    czysci cala plansze."""
    field = _field_with(3, hp=1)
    field.config.shockwave_fraction = 1.0
    inner, middle, outer = field.alive()
    outer_before = outer.hp
    res = field.apply_damage(inner, inner.hp)
    assert middle in res.destroyed
    assert outer.hp == outer_before


def test_shockwave_kills_are_reported():
    """Bez tego drugi okrag ginie bez wyplaty — monety znikaja po cichu."""
    field = _field_with(2, hp=1000)
    field.config.shockwave_fraction = 10.0
    inner, outer = field.alive()
    res = field.apply_damage(inner, inner.hp)
    assert set(res.destroyed) == {inner, outer}
```

`_field_with(3, hp=1)` daje trzy okręgi o HP 1 — jedna fala jest w stanie zabić sąsiada, więc test kaskady ma czego szukać.

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py -q`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'shockwave_fraction'`

- [ ] **Step 3: Add state, upgrade and config**

`game_state.py`, gałąź Okręgi:

```python
    upgrade_shockwave: int = 0        # warstwa 2, max 3
```

`upgrade_tree.py`, gałąź `rings`:

```python
    Upgrade("shockwave", "Fala uderzeniowa", "Smierc okregu rani nastepny",
            "rings", 3, 1.2, cost_multiplier=2.2, unlock_wave=10),
```

`config.py`:

```python
SHOCKWAVE_FRACTION_PER_LEVEL: float = 0.15
```

pole `shockwave_fraction: float = 0.0` i w `apply_upgrades`:

```python
        self.shockwave_fraction = (state.upgrade_shockwave
                                   * SHOCKWAVE_FRACTION_PER_LEVEL)
```

- [ ] **Step 4: Propagate exactly one step**

W `apply_damage`, po dopisaniu `ring` do `killed`:

```python
        if ring.hit(int(round(amount))):
            killed.append(ring)
            # Fala uderzeniowa. propagate=False w wywołaniu wtórnym, bo okrąg
            # zabity falą wywołałby własną i jedno trafienie zmiotłoby całą
            # planszę — propagacja ma być dokładnie o jeden krok.
            if propagate and self.config.shockwave_fraction > 0.0:
                neighbour = self.next_outward(ring)
                if neighbour is not None:
                    wave_dmg = ring.max_hp * self.config.shockwave_fraction
                    echo = self.apply_damage(neighbour, wave_dmg, propagate=False)
                    killed.extend(echo.destroyed)
```

- [ ] **Step 5: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 219 testów

- [ ] **Step 6: Commit (człowiek)**

```
feat: add shockwave upgrade
```

---

### Task 12: Przebicie

**Files:**
- Modify: `game_state.py`, `upgrade_tree.py`, `config.py`, `ring_field.py`
- Test: `tests/test_ring_field.py`

**Interfaces:**
- Consumes: `RingField.apply_damage`, `RingField.next_outward`.
- Produces:
  - `GameState.upgrade_pierce: int = 0`
  - `Config.pierce_fraction: float`

- [ ] **Step 1: Write the failing tests**

```python
def test_pierce_damages_the_next_ring():
    field = _field_with(2, hp=1000)
    field.config.pierce_fraction = 0.2
    inner, outer = field.alive()
    outer_before = outer.hp
    field.apply_damage(inner, 50)
    assert outer.hp == outer_before - 10


def test_pierce_applies_even_when_inner_survives():
    """Rozni sie tym od fali uderzeniowej — przebicie nie czeka na smierc."""
    field = _field_with(2, hp=1000)
    field.config.pierce_fraction = 0.2
    inner, outer = field.alive()
    field.apply_damage(inner, 10)
    assert inner.alive is True
    assert outer.hp < outer.max_hp


def test_pierce_hits_only_one_ring():
    field = _field_with(3, hp=1)
    field.config.pierce_fraction = 1.0
    inner, middle, outer = field.alive()
    outer_before = outer.hp
    field.apply_damage(inner, 1)
    assert outer.hp == outer_before


def test_pierce_percentage_has_no_ceiling():
    """20%/poz. bez sufitu — na poziomie 8 nastepny okrag obrywa mocniej
    niz pierwszy, i to jest zamierzone ujscie monet."""
    field = _field_with(2, hp=1000)
    field.config.pierce_fraction = 1.6
    inner, outer = field.alive()
    outer_before = outer.hp
    field.apply_damage(inner, 10)
    assert outer_before - outer.hp == 16
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ring_field.py -q`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'pierce_fraction'`

- [ ] **Step 3: Add state, upgrade and config**

`game_state.py`, gałąź Piłka:

```python
    upgrade_pierce: int = 0           # warstwa 3, bez sufitu
```

`upgrade_tree.py`, gałąź `ball`:

```python
    Upgrade("pierce", "Przebicie", "Trafienie rani takze nastepny okrag",
            "ball", None, 2.0, cost_multiplier=1.8, unlock_wave=25,
            requires="crit_chance"),
```

`config.py`:

```python
PIERCE_FRACTION_PER_LEVEL: float = 0.20
```

pole `pierce_fraction: float = 0.0` i w `apply_upgrades`:

```python
        self.pierce_fraction = state.upgrade_pierce * PIERCE_FRACTION_PER_LEVEL
```

- [ ] **Step 4: Apply pierce before the kill check**

W `apply_damage`, **przed** `if ring.hit(...)` — przebicie działa niezależnie od tego, czy pierwszy okrąg zginie:

```python
        if propagate and self.config.pierce_fraction > 0.0:
            neighbour = self.next_outward(ring)
            if neighbour is not None:
                echo = self.apply_damage(
                    neighbour, amount * self.config.pierce_fraction,
                    propagate=False)
                killed.extend(echo.destroyed)
```

Uwaga na kolejność: `killed` musi być zadeklarowane wyżej, a `next_outward` wywołane **zanim** `ring` zginie i wypadnie z `alive()`.

- [ ] **Step 5: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 223 testy

- [ ] **Step 6: Commit (człowiek)**

```
feat: add pierce upgrade
```

---

### Task 13: Słaby punkt

**Files:**
- Modify: `game_state.py`, `upgrade_tree.py`, `config.py`, `circle_ring.py`
- Test: `tests/test_circle_ring_types.py`

**Interfaces:**
- Consumes: `HitResult` (Task 7).
- Produces:
  - `GameState.upgrade_weak_point: int = 0`
  - `Config.weak_point_size: float` — szerokość łuku w stopniach, 0 = wyłączony
  - `Config.weak_point_multiplier: float = 5.0`
  - `CircleRing.weak_point_angle: float` — środek łuku, obraca się w `update`
  - `CircleRing.is_point_in_weak_point(angle: float) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
def test_weak_point_is_off_by_default():
    simple_ring = _ring()
    simple_ring.config.weak_point_size = 0.0
    assert simple_ring.is_point_in_weak_point(0.0) is False


def test_weak_point_covers_its_arc():
    simple_ring = _ring()
    simple_ring.config.weak_point_size = 40.0
    simple_ring.weak_point_angle = 90.0
    assert simple_ring.is_point_in_weak_point(90.0) is True
    assert simple_ring.is_point_in_weak_point(105.0) is True
    assert simple_ring.is_point_in_weak_point(150.0) is False


def test_weak_point_wraps_around_zero():
    simple_ring = _ring()
    simple_ring.config.weak_point_size = 40.0
    simple_ring.weak_point_angle = 0.0
    assert simple_ring.is_point_in_weak_point(355.0) is True
    assert simple_ring.is_point_in_weak_point(5.0) is True


def test_bounce_on_weak_point_multiplies_damage():
    simple_ring, ball_at_wall = _ring_and_ball()
    """Mnoznik staly x5 — rosnie tylko szerokosc luku."""
    simple_ring.config.weak_point_size = 360.0   # caly obwod, trafienie pewne
    simple_ring.config.weak_point_multiplier = 5.0
    res = simple_ring.check_collision(ball_at_wall)
    assert res.damage == simple_ring.config.ball_damage * 5.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_circle_ring_types.py -q`
Expected: FAIL — `AttributeError: 'CircleRing' object has no attribute 'is_point_in_weak_point'`

- [ ] **Step 3: Add state, upgrade and config**

`game_state.py`, gałąź Okręgi:

```python
    upgrade_weak_point: int = 0       # warstwa 3, max 3
```

`upgrade_tree.py`, gałąź `rings`:

```python
    Upgrade("weak_point", "Slaby punkt", "Ruchomy luk przyjmuje x5 obrazen",
            "rings", 3, 3.0, cost_multiplier=2.2, unlock_wave=25,
            requires="shockwave"),
```

`config.py`:

```python
WEAK_POINT_SIZE_PER_LEVEL: float = 20.0
BASE_WEAK_POINT_MULTIPLIER: float = 5.0
```

pola `weak_point_size: float = 0.0`, `weak_point_multiplier: float = BASE_WEAK_POINT_MULTIPLIER` i w `apply_upgrades`:

```python
        # Rośnie szerokość łuku, nie mnożnik — mnożnik skalujący się razem
        # z szerokością dawałby wzrost kwadratowy przy liniowym koszcie.
        self.weak_point_size = state.upgrade_weak_point * WEAK_POINT_SIZE_PER_LEVEL
        self.weak_point_multiplier = BASE_WEAK_POINT_MULTIPLIER
```

- [ ] **Step 4: Implement the arc on CircleRing**

W `CircleRing.__init__`:

```python
        # Słaby punkt startuje w losowym miejscu obwodu, żeby okręgi na planszy
        # nie miały go w jednej linii — inaczej wygląda jak błąd rysowania.
        self.weak_point_angle: float = 0.0
```

(ustaw losowo tam, gdzie `RingField` woła `spawn`, albo zostaw 0 i obracaj — obrót i tak rozjeżdża okręgi po sekundzie).

Metoda, wzorowana na istniejącej `is_point_in_hole`:

```python
    def is_point_in_weak_point(self, angle: float) -> bool:
        """Czy dany kąt obwodu leży w słabym punkcie."""
        if self.config.weak_point_size <= 0.0:
            return False
        half = self.config.weak_point_size / 2.0
        diff = abs((angle - self.weak_point_angle + 180.0) % 360.0 - 180.0)
        return diff <= half
```

W `update` obracaj łuk:

```python
        self.weak_point_angle = (self.weak_point_angle + 30.0 * dt) % 360.0
```

- [ ] **Step 5: Multiply damage on hit**

W `check_collision`, w gałęzi odbicia, przed zbudowaniem `HitResult`:

```python
        damage = self.config.ball_damage
        if self.is_point_in_weak_point(angle):
            damage *= self.config.weak_point_multiplier
        ...
        return HitResult(bounced=True, damage=damage)
```

- [ ] **Step 6: Draw it**

W `circle_ring.py` dodaj metodę i zawołaj ją na końcu `draw`, tuż po `_draw_band`:

```python
    def _draw_weak_point(self, surface: pygame.Surface) -> None:
        """Rysuje słaby punkt jaśniejszym odcieniem koloru okręgu.

        Kąty negowane i prostokąt o promieniu radius+thickness — dokładnie
        jak w _draw_band, bo pygame liczy kąty przeciwnie do kierunku
        przyjętego w tej grze, a łuk rysuje do wewnątrz od krawędzi.
        """
        if self.config.weak_point_size <= 0.0:
            return
        half = self.config.weak_point_size / 2.0
        start = self.weak_point_angle - half
        end = self.weak_point_angle + half
        outer = self.radius + self.thickness
        rect = pygame.Rect(self.cx - outer, self.cy - outer, outer * 2, outer * 2)
        bright = tuple(min(255, int(c * 1.6) + 40) for c in self.color)
        pygame.draw.arc(surface, bright, rect,
                        math.radians(-end), math.radians(-start),
                        self.thickness + 2)
```

Porównaj z istniejącym `_draw_band` (`circle_ring.py:200-230`) i dopasuj sposób budowania prostokąta, jeśli tam wygląda inaczej.

- [ ] **Step 7: Run the full suite and smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 227 testów

Run: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py`
Expected: kod wyjścia 124

- [ ] **Step 8: Commit (człowiek)**

```
feat: add rotating weak point upgrade
```

---

# ETAP 3 — prestiż i ekonomia

---

### Task 14: Kryształy zależne od fali

**Files:**
- Modify: `game_state.py:105-150` (`prestige`), nowe stałe i metoda; `ui/prestige_view.py:143`
- Test: `tests/test_game_state.py`

**Interfaces:**
- Consumes: `GameState.run_max_wave` (Task 2).
- Produces:
  - `PRESTIGE_MIN_WAVE: int = 10`, `CRYSTAL_SCALE: float = 3.0`, `CRYSTAL_EXPONENT: float = 1.5`
  - `GameState.crystals_on_prestige() -> int`
  - `GameState.upgrade_crystal_yield: int = 0`, `GameState.prestige_crystal_gain: int = 0`

- [ ] **Step 1: Write the failing tests**

```python
from game_state import PRESTIGE_MIN_WAVE, GameState


def test_no_crystals_below_minimum_wave():
    assert GameState(run_max_wave=9).crystals_on_prestige() == 0


def test_crystals_grow_with_the_wave_reached():
    """Poprzedni wzor (1 + prestige_count // 2) w ogole nie widzial fali."""
    low = GameState(run_max_wave=10).crystals_on_prestige()
    high = GameState(run_max_wave=40).crystals_on_prestige()
    assert low == 3
    assert high == 24


def test_crystals_at_target_run_length():
    assert GameState(run_max_wave=27).crystals_on_prestige() == 13


def test_crystal_bonuses_stack():
    st = GameState(run_max_wave=27, upgrade_crystal_yield=5,
                   prestige_crystal_gain=5)
    assert st.crystals_on_prestige() == 34


def test_prestige_uses_run_peak_not_current_wave():
    """Zduszenie z fali 10 na 9 nie moze odbierac zapracowanego prestizu."""
    st = GameState(wave=9, run_max_wave=10)
    assert st.prestige() is True


def test_prestige_awards_the_computed_crystals():
    st = GameState(wave=27, run_max_wave=27)
    st.prestige()
    assert st.prestige_crystals == 13
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: FAIL — `ImportError: cannot import name 'PRESTIGE_MIN_WAVE'`

- [ ] **Step 3: Add the constants, fields and formula**

`game_state.py`:

```python
PRESTIGE_MIN_WAVE: int = 10
CRYSTAL_SCALE: float = 3.0
CRYSTAL_EXPONENT: float = 1.5
```

pola w `GameState`:

```python
    upgrade_crystal_yield: int = 0    # warstwa 3, max 5
    prestige_crystal_gain: int = 0    # drzewko krysztalow, max 5
```

metoda:

```python
    def crystals_on_prestige(self) -> int:
        """Ile kryształów da prestiż teraz. Jedyne miejsce, w którym to liczymy.

        Wzór zależy od fali, bo poprzedni (1 + prestige_count // 2) w ogóle jej
        nie widział — prestiż na fali 10 dawał tyle samo co na fali 100, więc
        optymalną strategią był reset na minimum w kółko. Wykładnik 1.5
        sprawia, że pchanie się dalej opłaca się coraz bardziej za falę, ale
        coraz mniej za minutę; ten rozjazd jest momentem, w którym reset staje
        się decyzją, a nie rutyną.
        """
        if self.run_max_wave < PRESTIGE_MIN_WAVE:
            return 0
        base = CRYSTAL_SCALE * (self.run_max_wave / PRESTIGE_MIN_WAVE) ** CRYSTAL_EXPONENT
        yield_bonus = 1.0 + self.upgrade_crystal_yield * 0.10
        gain_bonus = 1.0 + self.prestige_crystal_gain * 0.15
        return max(1, int(base * yield_bonus * gain_bonus))
```

- [ ] **Step 4: Use it in prestige()**

W `prestige()` zamień warunek i wyliczenie:

```python
        if self.run_max_wave < PRESTIGE_MIN_WAVE:
            return False
        crystals = self.crystals_on_prestige()
```

Dopisz `prestige_crystal_gain` do zachowywanych pól permanentnych (obok `saved_prestige_coin_mult`).

- [ ] **Step 5: Remove the duplicated formula from the view**

`ui/prestige_view.py:143` — zamień:

```python
        crystals_gain = self.state.crystals_on_prestige()
```

- [ ] **Step 6: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 233 testy

- [ ] **Step 7: Commit (człowiek)**

```
fix: scale prestige crystals with the wave reached
```

---

### Task 15: Rozbudowane drzewko kryształów

**Files:**
- Modify: `upgrade_tree.py` (`PrestigeUpgrade`, `PRESTIGE_UPGRADES`), `game_state.py` (pola), `config.py` (`apply_upgrades`)
- Test: `tests/test_upgrade_tree.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `GameState.crystals_on_prestige` (Task 14).
- Produces:
  - `PrestigeUpgrade.cost_multiplier: float = 1.0`
  - `PrestigeUpgrade.cost_at_level(current_level: int) -> int`
  - `GameState.prestige_start_wave: int = 0`, `GameState.prestige_damage: int = 0`

- [ ] **Step 1: Write the failing tests**

```python
from upgrade_tree import PRESTIGE_UPGRADES, PrestigeUpgrade


def test_flat_cost_is_the_default():
    """Cztery istniejace wpisy nie moga zmienic ceny przez ten dodatek."""
    upg = PrestigeUpgrade("x", "X", "opis", 5, cost_crystals=3)
    assert upg.cost_at_level(0) == 3
    assert upg.cost_at_level(4) == 3


def test_scaling_cost_compounds():
    upg = PrestigeUpgrade("x", "X", "opis", 5, cost_crystals=4,
                          cost_multiplier=1.5)
    assert upg.cost_at_level(0) == 4
    assert upg.cost_at_level(2) == 9


def test_start_wave_upgrade_exists():
    ids = {u.id for u in PRESTIGE_UPGRADES}
    assert {"start_wave", "damage", "crystal_gain"} <= ids
```

w `tests/test_config.py`:

```python
def test_prestige_damage_multiplies_ball_damage():
    cfg = Config()
    plain = GameState(upgrade_ball_damage=4)
    boosted = GameState(upgrade_ball_damage=4, prestige_damage=4)
    cfg.apply_upgrades(plain)
    base = cfg.ball_damage
    cfg.apply_upgrades(boosted)
    assert cfg.ball_damage == int(round(base * 2.0))
```

w `tests/test_game_state.py`:

```python
def test_start_wave_sets_both_wave_and_run_peak():
    """Bez run_max_wave pierwsze fale nie liczylyby sie do krysztalow."""
    st = GameState(wave=30, run_max_wave=30, prestige_start_wave=5)
    st.prestige()
    assert st.wave == 11
    assert st.run_max_wave == 11
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: FAIL — `TypeError: unexpected keyword argument 'cost_multiplier'`

- [ ] **Step 3: Add scaling cost to PrestigeUpgrade**

```python
@dataclass
class PrestigeUpgrade:
    id: str
    name: str
    description: str
    max_level: int
    cost_crystals: int
    # Domyślna jedynka to koszt stały — cztery istniejące wpisy nie zmieniają
    # przez ten dodatek ani ceny, ani definicji.
    cost_multiplier: float = 1.0

    def cost_at_level(self, current_level: int) -> int:
        return int(round(self.cost_crystals * self.cost_multiplier ** current_level))
```

Zmień też `max_level` na `Optional[int]` i pozostałe trzy metody:

```python
    max_level: Optional[int]   # None = bez sufitu, jak w Upgrade

    def is_maxed(self, state: "GameState") -> bool:
        if self.max_level is None:
            return False
        return self.current_level(state) >= self.max_level

    def can_afford(self, state: "GameState") -> bool:
        return state.prestige_crystals >= self.cost_at_level(self.current_level(state))

    def purchase(self, state: "GameState") -> bool:
        if self.is_maxed(state) or not self.can_afford(state):
            return False
        state.spend_crystals(self.cost_at_level(self.current_level(state)))
        attr = f"prestige_{self.id}"
        setattr(state, attr, getattr(state, attr) + 1)
        return True
```

Sprawdź `ui/prestige_view.py:190` — rysuje `f"{upg.cost_crystals} krysztalow"`, więc musi przejść na `upg.cost_at_level(upg.current_level(self.state))`, inaczej pokaże cenę pierwszego poziomu na każdym.

- [ ] **Step 4: Extend the prestige table**

```python
PRESTIGE_UPGRADES: list[PrestigeUpgrade] = [
    PrestigeUpgrade("speed",        "Wrodzona predkosc",     "+10% bazowej predkosci na start", 10, 3),
    PrestigeUpgrade("hole_size",    "Wyczucie dziury",       "+8 stopni dziury na start",        5, 3),
    PrestigeUpgrade("coin_mult",    "Zlota raczka",          "+25% monet permanentnie",         10, 4),
    PrestigeUpgrade("extra_ball",   "Druga szansa",          "Dodatkowa pilka od startu",        3, 8),
    PrestigeUpgrade("start_wave",   "Rozbieg",               "Start na fali wyzszej o 2",        5, 6),
    PrestigeUpgrade("damage",       "Wrodzona sila",         "+25% obrazen pilki",            None, 5, cost_multiplier=1.5),
    PrestigeUpgrade("crystal_gain", "Rezonans krysztalow",   "+15% krysztalow za prestiz",       5, 10),
]
```

- [ ] **Step 5: Wire the effects**

`game_state.py` — pola `prestige_start_wave: int = 0`, `prestige_damage: int = 0`, oba dopisane do zachowywanych w `prestige()`. Na końcu `prestige()`, po przywróceniach:

```python
        # Rozbieg ustawia falę I szczyt runu. Bez szczytu pierwsze fale nie
        # liczyłyby się do kryształów przy następnym prestiżu.
        self.wave = 1 + self.prestige_start_wave * 2
        self.run_max_wave = self.wave
        self.max_wave_reached = max(self.max_wave_reached, self.wave)
```

`config.py`, w `apply_upgrades`, po wyliczeniu `self.ball_damage`:

```python
        prestige_damage_bonus = 1.0 + state.prestige_damage * 0.25
        self.ball_damage = max(1, int(round(self.ball_damage * prestige_damage_bonus)))
```

- [ ] **Step 6: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 238 testów

- [ ] **Step 7: Commit (człowiek)**

```
feat: expand the prestige tree
```

---

### Task 16: Seria

**Files:**
- Modify: `game_state.py`, `upgrade_tree.py`
- Test: `tests/test_game_state.py`

**Interfaces:**
- Consumes: `GameState.on_ring_destroyed`, `GameState.on_crushed` (istnieją).
- Produces:
  - `GameState.upgrade_combo: int = 0`, `GameState.combo_streak: int = 0`
  - `GameState.combo_multiplier() -> float`
  - `COMBO_MAX_MULTIPLIER: float = 3.0`

- [ ] **Step 1: Write the failing tests**

```python
def test_combo_does_nothing_without_the_upgrade():
    st = GameState()
    for _ in range(50):
        st.on_ring_destroyed()
    assert st.combo_multiplier() == 1.0


def test_combo_grows_with_the_streak():
    st = GameState(upgrade_combo=5)
    for _ in range(4):
        st.on_ring_destroyed()
    assert st.combo_multiplier() == pytest.approx(1.0 + 4 * 5 * 0.02)


def test_combo_is_capped():
    st = GameState(upgrade_combo=5)
    for _ in range(500):
        st.on_ring_destroyed()
    assert st.combo_multiplier() == COMBO_MAX_MULTIPLIER


def test_crush_resets_the_streak():
    st = GameState(upgrade_combo=5, wave=5)
    for _ in range(10):
        st.on_ring_destroyed()
    st.on_crushed()
    assert st.combo_streak == 0
    assert st.combo_multiplier() == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: FAIL — `AttributeError: 'GameState' object has no attribute 'combo_multiplier'`

- [ ] **Step 3: Implement**

`game_state.py`:

```python
COMBO_PER_LEVEL: float = 0.02
COMBO_MAX_MULTIPLIER: float = 3.0
```

pola: `upgrade_combo: int = 0`, `combo_streak: int = 0`

```python
    def combo_multiplier(self) -> float:
        """Mnożnik za serię zabójstw bez zduszenia, z sufitem.

        Sufit jest konieczny, bo seria rośnie z czasem gry, a nie z falą —
        bez niego gra zostawiona na noc mnożyłaby wypłatę przez tysiące.
        """
        if self.upgrade_combo <= 0:
            return 1.0
        raw = 1.0 + self.combo_streak * self.upgrade_combo * COMBO_PER_LEVEL
        return min(raw, COMBO_MAX_MULTIPLIER)
```

W `on_ring_destroyed`, przed wyliczeniem monet:

```python
        self.combo_streak += 1
```

i dołóż `* self.combo_multiplier()` do iloczynu `coins`.

W `on_crushed`:

```python
        self.combo_streak = 0
```

`upgrade_tree.py`, gałąź `economy`:

```python
    Upgrade("combo", "Seria", "+2% monet za kazdy okrag z rzedu",
            "economy", 5, 0.9, unlock_wave=10, requires="coin_multiplier"),
```

- [ ] **Step 4: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 242 testy

- [ ] **Step 5: Commit (człowiek)**

```
feat: add kill streak combo upgrade
```

---

### Task 17: Nocna zmiana

**Files:**
- Modify: `game_state.py:1-20` (stałe offline), `game_state.py:170-200` (`offline_earnings`), `upgrade_tree.py`
- Test: `tests/test_game_state.py`

**Interfaces:**
- Consumes: `GameState.offline_earnings` (istnieje).
- Produces:
  - `GameState.upgrade_night_shift: int = 0`
  - `GameState.offline_cap_seconds() -> float`

- [ ] **Step 1: Write the failing tests**

```python
def test_offline_cap_grows_with_night_shift():
    assert GameState().offline_cap_seconds() == 8 * 3600.0
    assert GameState(upgrade_night_shift=5).offline_cap_seconds() == 13 * 3600.0


def test_night_shift_raises_the_rate():
    plain = GameState(wave=10, last_played_at=1000.0)
    boosted = GameState(wave=10, last_played_at=1000.0, upgrade_night_shift=5)
    _, plain_coins = plain.offline_earnings(1000.0 + 3600.0)
    _, boosted_coins = boosted.offline_earnings(1000.0 + 3600.0)
    assert boosted_coins == pytest.approx(plain_coins * 2.5)


def test_night_shift_extends_the_capped_window():
    st = GameState(wave=10, last_played_at=0.0)
    st.last_played_at = 1.0
    elapsed, _ = st.offline_earnings(1.0 + 100 * 3600.0)
    assert elapsed == 8 * 3600.0
    st.upgrade_night_shift = 5
    elapsed, _ = st.offline_earnings(1.0 + 100 * 3600.0)
    assert elapsed == 13 * 3600.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: FAIL — `AttributeError: 'GameState' object has no attribute 'offline_cap_seconds'`

- [ ] **Step 3: Implement**

`game_state.py`:

```python
NIGHT_SHIFT_RATE_PER_LEVEL: float = 0.30
NIGHT_SHIFT_CAP_PER_LEVEL: float = 3600.0
```

pole `upgrade_night_shift: int = 0`

```python
    def offline_cap_seconds(self) -> float:
        """Ile najwyżej czasu poza grą jest naliczane."""
        return (OFFLINE_CAP_SECONDS
                + self.upgrade_night_shift * NIGHT_SHIFT_CAP_PER_LEVEL)
```

W `offline_earnings` zamień `min(elapsed, OFFLINE_CAP_SECONDS)` na `min(elapsed, self.offline_cap_seconds())` i domnóż stawkę:

```python
        rate *= 1.0 + self.upgrade_night_shift * NIGHT_SHIFT_RATE_PER_LEVEL
```

`upgrade_tree.py`, gałąź `economy`:

```python
    Upgrade("night_shift", "Nocna zmiana", "+30% zarobku offline i +1h limitu",
            "economy", 5, 1.5, cost_multiplier=1.9, unlock_wave=10,
            requires="auto_collector"),
```

- [ ] **Step 4: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 245 testów

- [ ] **Step 5: Commit (człowiek)**

```
feat: add night shift offline upgrade
```

---

### Task 18: Ujścia bez sufitu w ekonomii

**Files:**
- Modify: `game_state.py` (`add_coins`), `upgrade_tree.py`
- Test: `tests/test_game_state.py`

**Interfaces:**
- Consumes: `GameState.add_coins` (istnieje), `GameState.upgrade_crystal_yield` (Task 14).
- Produces: `GameState.upgrade_coin_multiplier_2: int = 0`

- [ ] **Step 1: Write the failing tests**

```python
def test_second_multiplier_stacks_on_the_first():
    st = GameState(upgrade_coin_multiplier=5, upgrade_coin_multiplier_2=4)
    st.add_coins(100.0)
    assert st.coins == pytest.approx(100.0 * 3.5 * 2.0)


def test_second_multiplier_has_no_ceiling():
    """Ujscie monet nie moze sie konczyc — przychod rosnie wykladniczo."""
    upg = next(u for u in UPGRADES if u.id == "coin_multiplier_2")
    assert upg.max_level is None
    assert upg.is_maxed(GameState(upgrade_coin_multiplier_2=999)) is False


def test_crystal_yield_is_a_tier_three_entry():
    upg = next(u for u in UPGRADES if u.id == "crystal_yield")
    assert upg.unlock_wave == 25
    assert upg.max_level == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_game_state.py -q`
Expected: FAIL — `TypeError: unexpected keyword argument 'upgrade_coin_multiplier_2'`

- [ ] **Step 3: Implement**

`game_state.py` — pole `upgrade_coin_multiplier_2: int = 0`, oraz w `add_coins`:

```python
        upgrade_mult = (1.0 + self.upgrade_coin_multiplier * 0.5) * \
                       (1.0 + self.upgrade_coin_multiplier_2 * 0.25)
```

`upgrade_tree.py`, gałąź `economy`:

```python
    Upgrade("coin_multiplier_2", "Mnoznik monet II", "+25% monet za poziom",
            "economy", None, 2.0, cost_multiplier=1.7, unlock_wave=10,
            requires="combo"),
    Upgrade("crystal_yield", "Krysztalowa zyla", "+10% krysztalow za prestiz",
            "economy", 5, 2.5, unlock_wave=25, requires="coin_multiplier_2"),
```

- [ ] **Step 4: Run the full suite and smoke test**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 248 testów

Run: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py`
Expected: kod wyjścia 124

- [ ] **Step 5: Commit (człowiek)**

```
feat: add uncapped economy sinks
```

---

# ETAP 4 — symulator i strojenie

---

### Task 19: Symulator balansu

**Files:**
- Create: `tools/measure_balance.py`

**Interfaces:**
- Consumes: `Config`, `GameState`, `RingField`, `UPGRADES`.
- Produces:
  - `RunReport` — dataclass: `minutes_to_wave: dict[int, float]`, `idle_coins_peak: float`, `never_bought: list[str]`, `crystals: int`
  - `simulate_run(seconds: float, seed: int = 42, hz: int = 120) -> RunReport`
  - `measure_income_per_minute(wave: int, seconds: float = 120.0, hz: int = 60) -> float` — używane przez Task 21

- [ ] **Step 1: Write the tool**

Utwórz `tools/measure_balance.py`:

```python
"""Pomiar balansu runu — uruchamiany ręcznie, nie jest testem.

Testy jednostkowe sprawdzają, czy reguła działa. Ten skrypt pokazuje, dokąd
reguła prowadzi po godzinie gry: ile minut zajmuje dojście do fali 10, 25 i 30,
ile monet leży bezczynnie i czy któreś ulepszenie nigdy nie jest opłacalne.

Piłka jest przybliżona tak samo jak w measure_ring_types.py: odbija się od
najbardziej wewnętrznego okręgu z częstotliwością predkosc / (2 * promien).
To wystarcza do balansu — chodzi o rzędy wielkości, nie o piksele.

Uruchomienie:
    ./.venv/Scripts/python.exe tools/measure_balance.py
"""

import math
import random
import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config              # noqa: E402
from formatting import short_number    # noqa: E402
from game_state import GameState       # noqa: E402
from ring_field import RingField       # noqa: E402
from upgrade_tree import UPGRADES      # noqa: E402

MILESTONES = (10, 25, 30)


@dataclass
class RunReport:
    minutes_to_wave: dict[int, float] = dc_field(default_factory=dict)
    idle_coins_peak: float = 0.0
    never_bought: list[str] = dc_field(default_factory=list)
    crystals: int = 0
    final_wave: int = 1


def _buy_greedily(state: GameState, config: Config) -> bool:
    """Kupuje najtańsze osiągalne ulepszenie. Zwraca True, gdy coś kupiono.

    Zachłannie, bo modelujemy gracza, który wydaje od razu — a to jest
    właśnie ten gracz, u którego widać, czy drzewko ma dość ujść.
    """
    affordable = [u for u in UPGRADES
                  if u.is_unlocked(state) and not u.is_maxed(state)
                  and u.can_afford(state)]
    if not affordable:
        return False
    cheapest = min(affordable,
                   key=lambda u: u.cost_at_level(u.current_level(state)))
    cheapest.purchase(state)
    config.apply_upgrades(state)
    return True


def simulate_run(seconds: float, seed: int = 42, hz: int = 120) -> RunReport:
    step = 1.0 / hz
    config, state = Config(), GameState()
    config.apply_upgrades(state)
    ring_field = RingField(config, (700, 520), hp=state.get_ring_hp(),
                           wave=state.wave, rng=random.Random(seed))
    report = RunReport()
    debt = 0.0
    now = 0.0
    since_shop = 0.0

    for _ in range(int(seconds / step)):
        now += step
        ring_field.update(step, hp=state.get_ring_hp(), wave=state.wave)

        inner = ring_field.innermost()
        if inner is not None:
            speed = math.hypot(config.initial_speed_x, config.initial_speed_y)
            balls = 1 + state.upgrade_multi_ball
            debt += balls * speed / max(1.0, 2.0 * inner.radius) * step
            while debt >= 1.0:
                debt -= 1.0
                state.on_bounce()
                result = ring_field.apply_damage(inner, config.ball_damage)
                for dead in result.destroyed:
                    state.on_ring_destroyed(
                        type_multiplier=dead.type.coin_multiplier)
                    if state.check_wave_progress():
                        config.apply_upgrades(state)
                if result.destroyed:
                    break

        if ring_field.is_crushed():
            state.on_crushed()
            config.apply_upgrades(state)
            ring_field.clear(hp=state.get_ring_hp(), wave=state.wave)

        # Sklep raz na sekundę symulowanego czasu — częściej nic nie zmienia,
        # a kosztuje przebieg po całej liście ulepszeń.
        since_shop += step
        if since_shop >= 1.0:
            since_shop = 0.0
            while _buy_greedily(state, config):
                pass
            report.idle_coins_peak = max(report.idle_coins_peak, state.coins)

        for milestone in MILESTONES:
            if state.max_wave_reached >= milestone and milestone not in report.minutes_to_wave:
                report.minutes_to_wave[milestone] = now / 60.0

    report.never_bought = [u.id for u in UPGRADES if u.current_level(state) == 0]
    report.crystals = state.crystals_on_prestige()
    report.final_wave = state.max_wave_reached
    return report


def measure_income_per_minute(wave: int, seconds: float = 120.0,
                              hz: int = 60) -> float:
    """Przychód na minutę przy warstwie danej fali wykupionej w całości.

    Punkt odniesienia dla INCOME_AT_UNLOCK: mierzymy moment, w którym gracz
    faktycznie kupuje daną warstwę, czyli gdy poprzednie są już jego.
    """
    step = 1.0 / hz
    config, state = Config(), GameState(wave=wave, run_max_wave=wave,
                                        max_wave_reached=wave)
    for upg in UPGRADES:
        if upg.unlock_wave <= wave and upg.max_level is not None:
            setattr(state, f"upgrade_{upg.id}", upg.max_level)
    config.apply_upgrades(state)
    ring_field = RingField(config, (700, 520), hp=state.get_ring_hp(),
                           wave=wave, rng=random.Random(7))
    debt = 0.0
    for _ in range(int(seconds / step)):
        ring_field.update(step, hp=state.get_ring_hp(), wave=wave)
        inner = ring_field.innermost()
        if inner is None:
            continue
        speed = math.hypot(config.initial_speed_x, config.initial_speed_y)
        balls = 1 + state.upgrade_multi_ball
        debt += balls * speed / max(1.0, 2.0 * inner.radius) * step
        while debt >= 1.0:
            debt -= 1.0
            state.on_bounce()
            result = ring_field.apply_damage(inner, config.ball_damage)
            for dead in result.destroyed:
                state.on_ring_destroyed(
                    type_multiplier=dead.type.coin_multiplier)
            if result.destroyed:
                break
    return state.total_coins_earned / (seconds / 60.0)


if __name__ == "__main__":
    rep = simulate_run(seconds=2 * 3600.0)
    print("=== RUN 2h ===")
    for milestone in MILESTONES:
        got = rep.minutes_to_wave.get(milestone)
        print(f"  minuty do fali {milestone:2d}: "
              f"{got:.0f}" if got else f"  fala {milestone} nieosiagnieta")
    print(f"  szczyt monet bezczynnych: {short_number(rep.idle_coins_peak)}")
    print(f"  nigdy nie kupione:        {rep.never_bought or 'brak'}")
    print(f"  krysztaly za run:         {rep.crystals}")
    print(f"  fala koncowa:             {rep.final_wave}")
    print("\n=== PRZYCHOD NA FALACH KOTWIC ===")
    for wave in (1, 10, 25):
        print(f"  fala {wave:2d}: {short_number(measure_income_per_minute(wave))}/min")
```

Uwaga: `state.max_wave_reached` przy `wave=1` startuje z 1, więc `simulate_run` mierzy kamienie milowe poprawnie od pierwszej klatki.

- [ ] **Step 2: Run it**

Run: `./.venv/Scripts/python.exe tools/measure_balance.py`
Expected: raport z czterema wierszami. Zapisz wynik — jest wejściem do Task 21.

- [ ] **Step 3: Commit (człowiek)**

```
feat: add run balance simulator
```

---

### Task 20: Tanie niezmienniki balansu

**Files:**
- Create: `tests/test_balance.py`

**Interfaces:**
- Consumes: `UPGRADES`, `INCOME_AT_UNLOCK`, `RING_PAYOUT_BASE`, `WAVE_GROWTH`.
- Produces: nic (same testy).

- [ ] **Step 1: Write the tests**

```python
from game_state import RING_PAYOUT_BASE, WAVE_GROWTH, GameState
from upgrade_tree import INCOME_AT_UNLOCK, UPGRADES


def test_higher_tiers_cost_more():
    """Warstwa 3 nie moze byc tansza od warstwy 1 — to znaczyloby, ze kotwice
    sie rozjechaly."""
    by_tier = {w: [u.base_cost for u in UPGRADES if u.unlock_wave == w]
               for w in INCOME_AT_UNLOCK}
    assert max(by_tier[1]) < min(by_tier[10])
    assert max(by_tier[10]) < min(by_tier[25])


def test_no_upgrade_is_strictly_dominated():
    """Zdominowane = drozsze i slabsze od sasiada w tej samej galezi
    i warstwie. Takiego wezla gracz nigdy racjonalnie nie kupi."""
    for branch in {u.branch for u in UPGRADES}:
        for wave in INCOME_AT_UNLOCK:
            group = [u for u in UPGRADES
                     if u.branch == branch and u.unlock_wave == wave]
            for a in group:
                for b in group:
                    if a is b or a.max_level is None or b.max_level is None:
                        continue
                    dominated = (a.base_cost > b.base_cost
                                 and a.max_level < b.max_level
                                 and a.cost_multiplier >= b.cost_multiplier)
                    assert not dominated, f"{a.id} zdominowane przez {b.id}"


def test_anchors_track_the_payout_curve():
    """Kotwice maja rosnac razem z wyplata, nie wlasnym zyciem."""
    for wave in (10, 25):
        payout = RING_PAYOUT_BASE * WAVE_GROWTH ** (wave - 1)
        rings_per_minute = INCOME_AT_UNLOCK[wave] / payout
        assert 300 < rings_per_minute < 600


def test_every_tier_has_at_least_one_uncapped_sink():
    """Bez ujscia bez sufitu warstwa zostaje wykupiona i gra sie zatrzymuje."""
    for wave in INCOME_AT_UNLOCK:
        tier = [u for u in UPGRADES if u.unlock_wave == wave]
        assert any(u.max_level is None for u in tier), f"warstwa {wave}"
```

- [ ] **Step 2: Run them**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_balance.py -q`
Expected: PASS. Jeśli któryś padnie — to jest sygnał do przestrojenia liczb, nie do poluzowania testu.

- [ ] **Step 3: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 252 testy w czasie poniżej 1,5 s

- [ ] **Step 4: Commit (człowiek)**

```
test: add cheap balance invariants
```

---

### Task 21: Kalibracja kotwic i wolny test regresji

**Files:**
- Modify: `upgrade_tree.py` (`INCOME_AT_UNLOCK`), `pytest.ini`
- Create: `tests/test_balance_slow.py`

**Interfaces:**
- Consumes: `simulate_run` (Task 19).
- Produces: `INCOME_AT_UNLOCK` przestrojone na faktycznej ekonomii.

- [ ] **Step 1: Register the marker**

`pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
addopts = -m "not slow"
markers =
    slow: symulacje balansu, uruchamiane jawnie przez -m slow
```

- [ ] **Step 2: Write the slow regression test**

```python
import pytest

from tools.measure_balance import measure_income_per_minute
from upgrade_tree import INCOME_AT_UNLOCK


@pytest.mark.slow
@pytest.mark.parametrize("wave", sorted(INCOME_AT_UNLOCK))
def test_anchor_matches_measured_income(wave):
    """Rozjazd kotwicy z rzeczywistoscia przestaje byc niewidoczny.

    Tolerancja 25%, bo symulacja przybliza pilke — chodzi o wychwycenie
    rozjazdu o rzad wielkosci, nie o precyzje.
    """
    measured = measure_income_per_minute(wave, seconds=120.0, hz=60)
    anchor = INCOME_AT_UNLOCK[wave]
    assert 0.75 * anchor <= measured <= 1.25 * anchor
```

Dopisz `measure_income_per_minute(wave, seconds, hz)` do `tools/measure_balance.py`.

- [ ] **Step 3: Run it and read the numbers**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_balance_slow.py -m slow -q`
Expected: prawdopodobnie FAIL — kotwice zmierzono przed naprawą `coins_on_bounce` i przed warstwami 2-3. **To jest oczekiwane**, spec zapowiada tę kalibrację.

- [ ] **Step 4: Retune the anchors**

Wstaw zmierzone wartości do `INCOME_AT_UNLOCK` i uruchom `tools/measure_balance.py`. Sprawdź cele ze spec:

```
minuty do fali 10 / 25 / 30      cel: ~20 / ~70 / ~100
monety lezace bezczynnie         cel: < 2 min przychodu
ulepszenia nigdy nieoplacalne    cel: brak
krysztaly za run                 cel: 11-15
```

Jeśli któryś cel jest chybiony, strojenie idzie przez `cost_minutes` pojedynczych ulepszeń, **nie** przez kotwice — kotwica opisuje ekonomię, `cost_minutes` opisuje zamiar projektowy.

- [ ] **Step 5: Run everything**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, szybki zestaw

Run: `./.venv/Scripts/python.exe -m pytest -m slow -q`
Expected: PASS

Run: `SDL_VIDEODRIVER=dummy timeout 8 ./.venv/Scripts/python.exe main.py`
Expected: kod wyjścia 124

- [ ] **Step 6: Commit (człowiek)**

```
fix: recalibrate cost anchors against measured income
```

---

## Kolejność i zależności

```
Etap 1:  T1 → T2 → T3 → T4
              T2 → T5
         T1,T3 → T6
Etap 2:  T7 → T8 → T9 → T10 → T11 → T12
                          T7 → T13
Etap 3:  T2 → T14 → T15
         T1 → T16 → T17 → T18
Etap 4:  wszystko → T19 → T20 → T21
```

T21 musi być ostatnie — kalibruje liczby na ekonomii, którą dopiero etapy 2 i 3 ustalają.
