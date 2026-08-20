# Drzewko rozwoju — warstwy, ujścia i rebalans

Data: 2026-08-19
Status: zatwierdzony, gotowy do planu implementacji

## Cel

Drzewko rozwoju kończy się szybciej, niż trwa gra. Całe drzewko z sufitem
kosztuje 11 770 monet, a zapis testowy ma 67 924 monety odłożone na fali 1 —
sześciokrotność wszystkiego, co zostało do kupienia. Po wyczerpaniu warstwy
startowej jedynym ujściem monet jest `ball_damage`, więc gra sprowadza się do
jednego przycisku wciskanego bez końca.

Projekt naprawia trzy niezależne usterki i dokłada treść na środkową i późną
część runu:

1. **Koszty stałe przy przychodzie wykładniczym.** `ring_payout()` rośnie jak
   `1.11^fala`, a `base_cost` to liczby wpisane na sztywno. Każde skończone
   drzewko przy takiej ekonomii zostanie wykupione — to niezgodność kształtu
   krzywych, nie kwestia strojenia.
2. **`coins_on_bounce` jako runaway.** Płaci stałe 0,5 monety za odbicie, więc
   na fali 1 mnoży przychód przez 35 (90/min → 3,2K/min), a na fali 25 jest
   już nieistotny. Zła jednostka nagrody: odbicia zamiast fal.
3. **Prestiż nagradzający za nic.** `crystals = 1 + prestige_count // 2` nie
   patrzy na osiągniętą falę. Prestiż na fali 10 daje tyle samo co na fali 100,
   więc optymalna strategia to reset na minimum w kółko, a każda minuta powyżej
   fali 10 jest czystą stratą.

Docelowe tempo: **run 1-2 h, prestiż koło fali 25-30.**

## Pomiary wyjściowe

Symulacja 10 min na falę, przybliżona piłka w konwencji
`tools/measure_ring_types.py`, pełne drzewko, `ball_damage` rosnące z falą:

| fala | wypłata/okrąg | przychód/min | okręgów/min |
|---:|---:|---:|---:|
| 1 | 15 | 3,2K | 213 |
| 5 | 23 | 8,3K | 361 |
| 10 | 38 | 15,8K | 416 |
| 15 | 65 | 22,5K | 346 |
| 20 | 109 | 45,4K | 417 |
| 25 | 184 | 80,0K | 435 |
| 30 | 309 | 151K | 489 |

Trzecia kolumna jest kluczem do modelu kosztu: przychód/min podzielony przez
wypłatę za okrąg wypłaszcza się na ~430 od fali 10, ale między falą 1 a 10
podwaja się. Kotwiczenie kosztu w samej wypłacie za okrąg zaniżyłoby warstwę
startową dwukrotnie względem reszty.

Bootstrap fali 1 (po naprawie odbić): 14 → 27 → 143 → 1,0K → 1,7K/min.
Średnia geometryczna rozpiętości ≈ 150/min.

## Wybrane podejście: koszt liczony w minutach gry

Odrzucone warianty:

- **Ręcznie wpisane koszty dobrane pomiarem.** Zostawia `base_cost=50.0`
  w definicji, tylko z lepszymi liczbami. To jest dokładnie ten mechanizm,
  który doprowadził do obecnego stanu — 25 rozsypanych stałych, z których
  każda musi być przestrojona ręcznie przy następnej zmianie ekonomii.
- **Generowanie stałych z deklaracji `cost_minutes` przez narzędzie.**
  Najczytelniejszy zamiar, ale dokłada krok budowania i rozdwaja źródło prawdy
  między deklarację a wygenerowaną liczbę. Za dużo maszynerii jak na tę grę.

Wybrane: **`cost_minutes` jako jedyny parametr kosztu, kotwica jako tablica
trzech zmierzonych liczb.**

```python
# upgrade_tree.py

# Zmierzony przychód na minutę w momencie, w którym gracz faktycznie kupuje
# daną warstwę: warstwę 1 podczas bootstrapu, warstwę 2 koło fali 10,
# warstwę 3 koło fali 25. Kotwica jest przychodem, nie wypłatą za okrąg —
# od fali 10 gracz zbiera ~430 okręgów na minutę i ta liczba się wypłaszcza,
# ale między falą 1 a 10 podwaja się, więc sama wypłata zaniżyłaby warstwę 1.
INCOME_AT_UNLOCK: dict[int, float] = {1: 150.0, 10: 15_000.0, 25: 90_000.0}
```

```python
@property
def base_cost(self) -> float:
    """Koszt pierwszego poziomu = ile minut gry ma kosztować."""
    return self.cost_minutes * INCOME_AT_UNLOCK[self.unlock_wave]
```

Zysk jest podwójny: trzy liczby zamiast 25, a jednostką staje się minuta gry,
która znaczy to samo na każdej fali. Ruszenie `WAVE_GROWTH` przestraja drzewko
samo — ta sama zasada, którą repo stosuje już w `ring_payout()` („jedna formuła
dla zniszczenia okręgu i dla naliczania offline — dwie niezależne właśnie
dlatego się rozjechały").

## Model danych

### Bramki falowe

```python
@dataclass
class Upgrade:
    ...
    cost_minutes: float          # zastępuje base_cost
    unlock_wave: int = 1         # warstwa: 1, 10 albo 25
```

```python
def is_unlocked(self, state) -> bool:
    if state.max_wave_reached < self.unlock_wave:
        return False
    return self.requires is None or getattr(state, f"upgrade_{self.requires}") > 0
```

Warunek idzie na `max_wave_reached`, **nie na `wave`** — `on_crushed()` cofa
falę o jeden, więc ulepszenie z warstwy 2 znikałoby graczowi po jednym
zduszeniu razem z kupionymi poziomami.

### Trzy pola fali

Każde ma jedno zadanie. Rozdzielenie wynikło ze sprzeczności: bramka warstw nie
może resetować się przy prestiżu (gracz traciłby odkrytą treść), a wzór na
kryształy musi (inaczej drugi prestiż płaciłby za falę osiągniętą w pierwszym
runie).

| pole | znaczenie | spada przy zduszeniu | zeruje przy prestiżu |
|---|---|:---:|:---:|
| `wave` | bieżąca trudność | tak | tak |
| `run_max_wave` | szczyt tego runu → kryształy | nie | tak |
| `max_wave_reached` | szczyt kiedykolwiek → bramki warstw | nie | nie |

Wynikowa reguła: **treść odblokowuje się na stałe, zakupy resetują.** Po
prestiżu warstwa 2 jest widoczna od pierwszej fali, ale kosztuje 10-30K, więc
i tak jest nieosiągalna, dopóki gracz nie dojedzie z powrotem. System reguluje
się sam, bez dodatkowej logiki.

Oba nowe pola aktualizuje `check_wave_progress()`.

## Warstwa 1 (fala 1) — korekty, nie przebudowa

Przeliczenie obecnych kosztów na `cost_minutes` przy kotwicy 150/min pokazało,
że są **prawie dokładnie takie, jakie powinny być** dla warstwy tutorialowej
(`ball_speed` 50 = 0,33 min, `auto_collector` 500 = 3,33 min). Warstwa 1 nie
była za tania — problemem było to, że po niej nic nie ma.

Potwierdza to zapis testowy: `upgrade_ball_damage: 0` przy 67 924 monetach,
mimo że ulepszenie jest odblokowane (wymaga `ball_speed`, gracz ma poziom 2)
i kosztuje 200 monet. Jedyne działające ujście monet zostało nietknięte — to
sygnał o czytelności drzewka, nie o cenach. Poza zakresem tego projektu,
odnotowane jako obserwacja dla przyszłej pracy nad UI.

Dwie zmiany:

| ulepszenie | zmiana | uzasadnienie |
|---|---|---|
| `coins_on_bounce` | efekt: **1% wypłaty za okrąg** na poziom zamiast stałych 0,5 | skaluje się z falą; przestaje być runawayem na starcie i martwym poziomem w późnej grze |
| `multi_ball` | maks. 2 → **3** | dodatkowe ujście w warstwie startowej |

Frakcja 1% wybrana pomiarem spośród trzech kandydatów:

| frakcja | fala 10 | fala 25 |
|---|---|---|
| 0,5% | 13,2K/min | 84K/min |
| **1,0%** | **15,1K/min** | **93,5K/min** |
| 1,5% | 17,0K/min | 103K/min |
| dziś (stałe 0,5) | 16,6K/min | 80,0K/min |

1% zostawia falę 10 praktycznie bez zmian względem dziś, a naprawia falę 25 —
leczy chorobę zamiast przestawiać grę.

## Warstwa 2 (fala 10) — kotwica 15 000/min

| id | nazwa | gałąź | efekt | maks | `cost_minutes` | koszt 1. poz. | ×/poz. |
|---|---|---|---|---:|---:|---:|---:|
| `crit_chance` | Trafienie krytyczne | ball | +5%/poz. szansy na ×3 obrażenia | 5 | 0,7 | 10,5K | 2,0 |
| `shockwave` | Fala uderzeniowa | rings | gdy okrąg ginie, następny na zewnątrz dostaje 15%/poz. **maks. HP okręgu, który zginął** | 3 | 1,2 | 18K | 2,2 |
| `combo` | Seria | economy | +2%/poz. monet za każdy okrąg z rzędu, sufit ×3; licznik `combo_streak` zeruje `on_crushed()` | 5 | 0,9 | 13,5K | 2,0 |
| `night_shift` | Nocna zmiana | economy | +30%/poz. stawki offline i +1 h limitu (8 h → 13 h na maks.) | 5 | 1,5 | 22,5K | 1,9 |
| `coin_multiplier_2` | Mnożnik monet II | economy | +25%/poz. monet | **∞** | 2,0 | 30K | 1,7 |

Część z sufitem pochłania ~1,5 M, czyli 30-40 min runu. `Mnożnik monet II`
zostaje ujściem na nadwyżkę.

## Warstwa 3 (fala 25) — kotwica 90 000/min

| id | nazwa | gałąź | efekt | maks | `cost_minutes` | koszt 1. poz. | ×/poz. |
|---|---|---|---|---:|---:|---:|---:|
| `pierce` | Przebicie | ball | trafienie zadaje 20%/poz. obrażeń także **jednemu** następnemu okręgowi na zewnątrz; procent nie ma sufitu na 100% | **∞** | 2,0 | 180K | 1,8 |
| `crit_power` | Siła krytyka | ball | mnożnik krytyka +1,0/poz. (start ×3) | **∞** | 2,5 | 225K | 1,8 |
| `weak_point` | Słaby punkt | rings | obracający się łuk **szerokości 20°/poz.** przyjmujący obrażenia ×5 (mnożnik stały, rośnie tylko szerokość) | 3 | 3,0 | 270K | 2,2 |
| `crystal_yield` | Kryształowa żyła | economy | +10%/poz. kryształów za prestiż | 5 | 2,5 | 225K | 2,0 |

`crystal_yield` kosztuje ~7 M na komplecie — celowo cel na kilka runów, nie na
jeden. Stoi w gałęzi monet, a nie w drzewku prestiżu, żeby decyzja „jeszcze
pięć fal czy reset" miała po obu stronach coś do kupienia. Ulepszenie kupowane
za monety, które zwiększa zysk z resetu, wiąże obie pętle zamiast stawiać je
obok siebie.

## Prestiż

### Wzór na kryształy

```python
PRESTIGE_MIN_WAVE: int = 10
CRYSTAL_SCALE: float = 3.0
CRYSTAL_EXPONENT: float = 1.5

def crystals_on_prestige(self) -> int:
    """Ile kryształów da prestiż teraz. Jedyne miejsce, w którym to liczymy.

    Wzór zależy od fali, bo poprzedni (1 + prestige_count // 2) w ogóle jej nie
    widział — prestiż na fali 10 dawał tyle samo co na fali 100. Wykładnik 1.5
    sprawia, że pchanie się dalej opłaca się coraz bardziej za falę, ale coraz
    mniej za minutę; ten rozjazd jest momentem, w którym reset staje się
    decyzją, a nie rutyną. Przy wzroście liniowym optymalny gracz zawsze
    resetuje natychmiast po minimum.
    """
    if self.run_max_wave < PRESTIGE_MIN_WAVE:
        return 0
    base = CRYSTAL_SCALE * (self.run_max_wave / PRESTIGE_MIN_WAVE) ** CRYSTAL_EXPONENT
    yield_bonus = 1.0 + self.upgrade_crystal_yield * 0.10
    gain_bonus = 1.0 + self.prestige_crystal_gain * 0.15
    return max(1, int(base * yield_bonus * gain_bonus))
```

| fala prestiżu | kryształy | z pełnymi bonusami (×2,6) |
|---:|---:|---:|
| 10 (minimum) | 3 | 7 |
| 20 | 8 | 22 |
| 27 (cel runu) | 13 | 34 |
| 40 | 24 | 63 |

`ui/prestige_view.py:143` przestaje liczyć cokolwiek i woła
`state.crystals_on_prestige()`. Dziś ta sama formuła stoi w dwóch miejscach
(`game_state.py:118` i widok) i może się rozjechać.

Przy okazji naprawia się cicha usterka: `prestige()` sprawdza `self.wave >= 10`,
więc zduszenie z fali 10 na 9 odbiera prestiż, na który gracz zapracował.
Warunek idzie na `run_max_wave`.

### Drzewko kryształów

`PrestigeUpgrade` dostaje `cost_multiplier: float = 1.0`. Domyślna jedynka
zachowuje stały koszt, więc cztery istniejące wpisy nie wymagają żadnej zmiany.

| ulepszenie | efekt | maks | koszt | ×/poz. |
|---|---|---:|---:|---:|
| Wrodzona prędkość | +10% bazowej prędkości | 5 → **10** | 3 | 1,0 |
| Wyczucie dziury | +8° dziury na start | 5 | 3 | 1,0 |
| Złota rączka | +25% monet | 5 → **10** | 4 | 1,0 |
| Druga szansa | piłka od startu | 2 → **3** | 8 | 1,0 |
| **Rozbieg** (`start_wave`) | start na fali 1 + 2/poz. | 5 | 6 | 1,0 |
| **Wrodzona siła** (`damage`) | +25% obrażeń piłki | **∞** | 5 | 1,5 |
| **Rezonans kryształów** (`crystal_gain`) | +15% kryształów za prestiż | 5 | 10 | 1,0 |

Część z sufitem to 189 kryształów ≈ 15 runów, czyli 20-30 godzin gry.

`Rozbieg` ustawia `wave` **i** `run_max_wave` na falę startową zaraz po
prestiżu. Bez tego gracz z `Rozbiegiem` na poziomie 5 zaczynałby run na fali 11
z `run_max_wave = 1` i pierwsze dziesięć fal nie liczyłoby się do kryształów.

Odrzucone: **„Pamięć mięśniowa"** (zachowujesz N poziomów `ball_damage` przez
prestiż). Robiła to samo co `Rozbieg` — skracała bootstrap — tylko okrężnie
i wymagała wyjątku w resecie `prestige()`.

## Przepływ obrażeń

### Problem

`CircleRing.check_collision()` zwraca `bool`, więc `main.py:369-376` musi
rekonstruować zdarzenie po skutkach ubocznych. Komentarz w kodzie przyznaje to
wprost: „check_collision zwraca False i przy braku kolizji, i przy przelocie
przez dziurę — odróżnia je dopiero spadek HP bez odbicia".

Po dodaniu warstw 2 i 3 to przestaje wystarczać. Gorzej: pętla zakłada
**najwyżej jeden zabity okrąg na kolizję** (`if was_alive and not ring.alive:`
dla pojedynczego `ring`). Fala uderzeniowa to łamie — drugi okrąg umarłby bez
wypłaty, bez cząstek i bez postępu fali. Założenie nie jest nigdzie zapisane,
żyje w kształcie warunku, więc złamanie byłoby ciche: nie błąd, tylko gubione
monety.

### Rozwiązanie

Krytyk, przebicie i fala uderzeniowa to trzy ulepszenia, ale jeden moment
w grze: obrażenia lądują na okręgu. Dostaje własną nazwę i jedno miejsce.

```python
# circle_ring.py
@dataclass(frozen=True)
class HitResult:
    """Co się stało przy jednym kontakcie piłki z okręgiem.

    Zastępuje bool, bo pętla główna musiała odróżniać dziurę od pudła przez
    porównanie HP sprzed i po — a po dodaniu fali uderzeniowej jedno trafienie
    może zabić dwa okręgi i ta rekonstrukcja przestaje być możliwa.
    """
    bounced: bool = False
    through_hole: bool = False
    crit: bool = False
    damage: float = 0.0
    destroyed: tuple["CircleRing", ...] = ()

    def __bool__(self) -> bool:
        return self.bounced or self.through_hole
```

```python
# ring_field.py
def apply_damage(self, ring: CircleRing, amount: float,
                 propagate: bool = True) -> HitResult:
    """Zadaje obrażenia okręgowi wraz ze wszystkim, co się z nimi niesie.

    Krytyk, przebicie i fala uderzeniowa to trzy ulepszenia, ale jeden moment
    w grze. Trzymanie ich tutaj, a nie w CircleRing, zostawia okręgowi
    geometrię, a polu — oddziaływania między okręgami, których pojedynczy
    okrąg z definicji nie widzi. Sam wymóg danych (przebicie i fala potrzebują
    NASTĘPNEGO okręgu) wskazuje tę warstwę.

    propagate=False dla wywołań wtórnych: fala uderzeniowa propaguje dokładnie
    o jeden krok, inaczej okrąg zabity falą wywołałby własną i powstałaby
    kaskada przez całą planszę.
    """
```

Przepływ:

```
Ball ──► CircleRing.check_collision()       geometria: gdzie, dziura czy odbicie
             │ zamiar zadania obrażeń
             ▼
        RingField.apply_damage()            krytyk → przebicie → śmierć → fala
             │ HitResult z listą zabitych
             ▼
        main.py: for ring in result.destroyed:   wypłata, cząstki, fala, osiągnięcia
```

`destroyed` jest krotką od pierwszej linijki, jeszcze zanim cokolwiek potrafi
zabić dwa okręgi — żeby niepisane założenie nie wróciło.

Krytyk losuje wstrzykiwany `random.Random`, tak jak `pick_type(wave, rng)`.
Losowanie odbywa się raz, w jednym miejscu, więc dziura i odbicie nie mogą mieć
różnych szans.

## Obsługa błędów

| ryzyko | zabezpieczenie |
|---|---|
| `INCOME_AT_UNLOCK[unlock_wave]` — `KeyError`, gdy ktoś doda ulepszenie z `unlock_wave=15` | walidacja przy imporcie modułu: każdy `unlock_wave` musi być kluczem tablicy. Pada przy starcie, nie po 40 minutach gry |
| stary zapis bez `max_wave_reached` → domyślne 0 → gracz z falą 30 traci dostęp do warstw i do prestiżu | migracja w `load_game`: gdy `max_wave_reached == 0`, ustaw oba nowe pola na `wave` z zapisu |
| kaskada fali uderzeniowej przez całą planszę | `propagate=False` w wywołaniach wtórnych — propagacja dokładnie o jeden krok |
| krytyk nietestowalny przez globalny `random` | wstrzykiwany `random.Random`, idiom już obecny w `ring_types.pick_type` |

Poza tym `save_manager.load_game` filtruje nieznane pola i daje brakującym
wartości domyślne z dataclassy, więc 15 nowych pól w `GameState` nie
unieważnia żadnego zapisu i nie wymaga bumpu `SAVE_VERSION`. Migracja
`max_wave_reached` jest jedynym wyjątkiem, bo tam domyślne zero jest błędne,
a nie tylko puste.

## Testy

Kolejność: test przed implementacją dla każdego mechanizmu. Baza to 178
przechodzących testów w 0,81 s — musi zostać zielona.

**Szybkie testy jednostkowe** (budżet < 0,2 s):

- bramka falowa: blokuje poniżej `unlock_wave`; nie blokuje się z powrotem po
  zduszeniu; przeżywa prestiż
- trzy pola fali: `wave` spada przy zduszeniu, `run_max_wave` nie,
  `run_max_wave` zeruje się przy prestiżu, `max_wave_reached` nie
- `crystals_on_prestige()`: rośnie z falą, zwraca 0 poniżej minimum, widok woła
  tę samą funkcję (test na brak drugiej kopii formuły)
- `apply_damage`: krytyk z ustalonym ziarnem, przebicie trafia następny okrąg,
  fala uderzeniowa **nie kaskaduje**
- `HitResult.destroyed` zawiera oba okręgi, gdy fala dobija drugi → wypłata za
  oba, postęp fali za oba
- `base_cost` z `cost_minutes` × kotwica; walidacja `unlock_wave` przy imporcie
- `coins_on_bounce` skaluje się z falą (1% wypłaty, nie stała)
- migracja starego zapisu bez `max_wave_reached`

**Symulator balansu** — `tools/measure_balance.py`, w konwencji istniejącego
`measure_ring_types.py` (narzędzie uruchamiane ręcznie, nie test). Symuluje
pełny run z zachłannym kupowaniem i raportuje:

```
minuty do fali 10 / 25 / 30      cel: ~20 / ~70 / ~100
monety leżące bezczynnie         cel: < 2 min przychodu
ulepszenia nigdy nieopłacalne    cel: brak
kryształy za run                 cel: 11-15
```

**Test regresji balansu** — podzielony, żeby strojenie nie zgniło po raz drugi:

- w zestawie domyślnym: **tanie niezmienniki bez symulacji** — koszt rośnie
  monotonicznie z warstwą, żadne ulepszenie nie jest zdominowane (droższe
  i słabsze od innego w tej samej gałęzi), `INCOME_AT_UNLOCK` zgodne
  z `ring_payout()` co do rzędu wielkości
- pod `@pytest.mark.slow`, wyłączone domyślnie: skrócona symulacja 120 s przy
  60 Hz sprawdzająca, że zmierzony przychód mieści się w ±25% tablicy kotwic

Podział wynika z obserwacji, że zestaw chodzący 0,8 s uruchamia się odruchowo,
a 30-sekundowy przestaje być uruchamiany. Test, którego nikt nie odpala, nie
chroni przed niczym.

## Zakres zmian

| plik | zmiana | rozmiar |
|---|---|---|
| `upgrade_tree.py` | `cost_minutes`, `unlock_wave`, `INCOME_AT_UNLOCK`, 9 nowych ulepszeń, `cost_multiplier` w prestiżu, 3 nowe prestiżowe | duża |
| `game_state.py` | 2 nowe pola fali, 9 pól ulepszeń, 3 pola prestiżu, `combo_streak` (15 nowych pól łącznie), `crystals_on_prestige()`, naprawa `on_bounce`, `prestige()` na `run_max_wave` | duża |
| `ring_field.py` | `apply_damage()` — krytyk, przebicie, fala uderzeniowa | średnia |
| `circle_ring.py` | `HitResult`, obrażenia przez `RingField`, słaby punkt | średnia |
| `config.py` | nowe pola pochodne w `apply_upgrades` | średnia |
| `main.py` | konsumpcja `HitResult`, pętla po `destroyed` | średnia |
| `ui/tree_view.py` | stan „zablokowane falą" + etykieta „od fali N" | mała |
| `ui/prestige_view.py` | woła `crystals_on_prestige()` | mała |
| `save_manager.py` | migracja `max_wave_reached` | mała |
| `tools/measure_balance.py` | nowy plik | nowy |
| `tests/` | ~25 nowych testów | duża |

## Kolejność wdrożenia

Projekt jest duży, więc dzieli się na cztery etapy. Każdy kończy się grywalną
grą i zielonym zestawem testów — nie ma etapu, po którym gra jest zepsuta.

**Etap 1 — model kosztu i bramki.** `cost_minutes`, `INCOME_AT_UNLOCK`,
`unlock_wave`, dwa nowe pola fali, migracja zapisu, stan „zablokowane falą"
w `tree_view`, naprawa `coins_on_bounce`, sufit `multi_ball`. Po etapie:
warstwa 1 przestrojona, bramki działają, warstwy 2 i 3 są jeszcze puste.
Bez ryzyka dla fizyki.

**Etap 2 — przepływ obrażeń.** `HitResult`, `RingField.apply_damage()`,
przepięcie `main.py`, a na tym krytyk, fala uderzeniowa, przebicie i słaby
punkt. **Etap o najwyższym ryzyku** — dotyka kodu kolizji, który już raz miał
błędy ze swept i cooldownami. `HitResult` i `apply_damage` idą pierwsze,
z zachowaniem identycznym jak dziś, i dopiero na zielonych testach dokładane są
mechaniki.

**Etap 3 — prestiż i ekonomia.** `crystals_on_prestige()` jako jedyne źródło,
`run_max_wave` w warunku prestiżu, `cost_multiplier` w `PrestigeUpgrade`, trzy
nowe ulepszenia prestiżu, `combo`, `night_shift`, `coin_multiplier_2`,
`crystal_yield`, przepięcie `prestige_view`.

**Etap 4 — symulator i strojenie.** `tools/measure_balance.py`, kalibracja
`INCOME_AT_UNLOCK` na naprawionej ekonomii (obecne wartości zmierzono przed
etapami 2 i 3, więc po nich wymagają potwierdzenia), testy regresji balansu.

Liczby kosztów w tym dokumencie są **projektowym punktem wyjścia, nie wynikiem
końcowym** — etap 4 jest miejscem, w którym mogą się zmienić, i to jest
zaplanowane, a nie porażka strojenia.

## Świadomie poza zakresem

- **Czytelność drzewka.** Zapis testowy pokazuje, że gracz nie kupił jedynego
  działającego ujścia monet, mimo że było odblokowane i tanie. To problem
  prezentacji, nie balansu — osobny cykl.
- **Sprawczość gracza.** Projekt typów okręgów odnotował, że gracz niczego nie
  celuje. To ograniczenie obowiązuje nadal: żadne nowe ulepszenie nie zakłada
  decyzji taktycznej w trakcie rozgrywki.
- **Ulepszenia zmieniające fizykę piłki** (naprowadzanie, grawitacja
  kierunkowa, rozszczepienie). Świadomie odrzucone — dotykałyby kodu kolizji,
  który już raz miał błędy ze swept i cooldownami.
