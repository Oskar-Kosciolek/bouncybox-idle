# Typy okręgów — projekt

Data: 2026-08-14
Status: zatwierdzony, gotowy do planu implementacji

## Cel

Okręgi są dziś nierozróżnialne: każdy ma te same HP, to samo tempo zwężania i tę
samą wypłatę. Trudność rośnie wyłącznie przez liczby (HP okręgu, prędkość
zwężania), więc plansza na fali 30 wygląda jak na fali 3, tylko szybciej.

Typy okręgów wprowadzają trzy rzeczy naraz, jednym mechanizmem:

- **rytm** — przeważnie zwykły okrąg, co jakiś czas inny,
- **krzywa trudności** — skład planszy przesuwa się z falami,
- **zróżnicowanie nagrody** — każdy typ płaci inaczej.

## Ograniczenie wyjściowe: gracz nie celuje

Piłka odbija się sama, power-upy zbiera automatycznie przez kolizję, dziury
trafia przypadkiem. Jedyne wejście gracza to zakupy i klawisze R/F5/F6.

Z tego wynika twarde ograniczenie projektowe: **typy nie mogą być wyborem
taktycznym**, bo gracz niczego nie wybiera. Mogą być wyłącznie teksturą,
rytmem i zróżnicowaniem wypłaty. Każdy typ, którego wartość opiera się na
decyzji gracza („zostaw pancerny na później"), jest w tej grze pusty.

Sprawczość gracza (celowanie, popychanie piłki) to osobny, późniejszy cykl
projektowy. Ten projekt świadomie jej nie zakłada. Gdy się pojawi, typy będzie
można wzbogacić, nie przepisując ich.

## Wybrane podejście: typ jako dane

Odrzucone warianty:

- **Podklasy `CircleRing`** — `CircleRing` już dziś odpowiada za HP, dziury,
  kolizje i rysowanie, więc każda podklasa dziedziczy cały ten ciężar. Gorzej:
  okrąg dzielący się musiałby po śmierci sięgnąć do `RingField`, co odwraca
  kierunek zależności (dziś pole zna okręgi, nie odwrotnie).
- **Komponenty zachowań** (`RingBehavior` z hakami) — jedyny wariant skalujący
  się do dowolnych zachowań, ale to warstwa pośrednia zbudowana pod problem,
  którego nie mamy. Pięć typów nie uzasadnia systemu pluginów. Zostaje jako
  ścieżka wyjścia, gdyby typów mocno przybyło.

Wybrane: **tabela typów jako dane, `RingField` jako wykonawca**. Zgodne z
idiomem, którego repo już używa wszędzie indziej — `UPGRADES`,
`PRESTIGE_UPGRADES`, `ACHIEVEMENTS`, `POWERUP_UNLOCK_WAVE` to tabele danych,
nie hierarchie klas. Nowy typ okręgu jest jedną linią na liście, tak jak nowe
ulepszenie jest dziś jedną linią.

Znane ograniczenie: zachowanie, którego nie da się sprowadzić do liczby
(podział), wymaga jawnego rozgałęzienia w `RingField`. Przy pięciu typach to
jedno miejsce — akceptowalne. Przy piętnastu należałoby wrócić do wariantu
komponentowego.

## Model danych

```python
@dataclass(frozen=True)
class RingType:
    id: str
    name: str
    color: tuple[int, int, int]
    hp_multiplier: float = 1.0       # względem state.get_ring_hp()
    shrink_multiplier: float = 1.0   # mnożnik prędkości zwężania
    coin_multiplier: float = 1.0     # mnożnik wypłaty
    splits_into: int = 0             # ile mniejszych okręgów po śmierci
    thickness: int = 4               # grubość linii przy rysowaniu
    unlock_wave: int = 1             # od której fali może wypaść
    weight: float = 1.0              # waga losowania na fali odblokowania
    weight_per_wave: float = 0.0     # jak waga zmienia się z każdą kolejną falą
```

Waga efektywna:

```
effective_weight(typ, fala) = max(0, typ.weight + typ.weight_per_wave * (fala - typ.unlock_wave))
```

Te dwie liczby są całą krzywą trudności. Zwykły okrąg dostaje ujemny przyrost,
specjalne dodatni — skład planszy przesuwa się z falami sam, bez osobnego
mechanizmu.

## Lista typów

| Typ | HP | Zwężanie | Monety | Dzieli się | Od fali | Waga | Przyrost/falę |
|---|---|---|---|---|---|---|---|
| zwykły | 1,0× | 1,0× | 1,0× | — | 1 | 10,0 | −0,35 |
| kruchy | 0,15× | 1,0× | 3,0× | — | 2 | 2,0 | 0,0 |
| pancerny | 3,0× | 1,0× | 2,5× | — | 4 | 1,0 | +0,25 |
| dzielący się | 0,6× | 1,0× | 0,6× | 2 | 6 | 0,5 | +0,15 |
| boss | 4,0× | 0,5× | 8,0× | — | co 10 fal | poza pulą | — |

**Boss nie bierze udziału w losowaniu ważonym.** Jest stawiany deterministycznie
(patrz niżej), więc jego wagi są nieużywane — w tabeli danych ma `weight = 0`,
a kod pomija go przy budowaniu puli losowania.

Skład planszy wynikający z tych wag:

| Fala | zwykły | kruchy | pancerny | dzielący się |
|---|---|---|---|---|
| 4 | 75% | 17% | 8% | — |
| 10 | 55% | 16% | 20% | 9% |
| 20 | 26% | 15% | 39% | 20% |
| 30 | — | 15% | 55% | 30% |

Waga zwykłego okręgu osiąga zero dokładnie na fali 30 (10 − 0,35 × 29 < 0) i od
tego momentu plansza składa się wyłącznie z typów specjalnych. To zamierzone.
Rozkłady wyliczone z powyższych wag, nie oszacowane.

### Dlaczego pancerz idzie przez HP, a nie przez odporność na obrażenia

Pierwotny pomysł zakładał mnożnik przyjmowanych obrażeń (np. 0,35×). Nie
zadziała: `config.ball_damage` wynosi `1` i **żadne ulepszenie go nie zmienia**.
Mnożnik 0,35 od jedynki po zaokrągleniu w górę wraca do jedynki — pancerz nie
robiłby nic. Mnożnik HP daje ten sam efekt (żyje 3× dłużej) bez pułapki
zaokrągleń. Pole `damage_taken` nie istnieje w modelu.

Gdyby kiedyś pojawiło się ulepszenie zwiększające `ball_damage`, odporność
procentowa stanie się sensowna i można ją dodać osobno.

### Dlaczego nie ma okręgu regenerującego

Rozważany i odrzucony. Bez celowania gracz nie ma wpływu na to, czy przebije
regenerację; jeśli nie przebije, okrąg jest nieśmiertelny i gwarantuje
zduszenie. To porażka, przy której gracz nie mógł nic zrobić, w grze, którą się
głównie ogląda.

Gorzej: stała regeneracja działa **odwrotnie do krzywej trudności**. Początkujący
z niskim DPS trafia na mur nie do przejścia, a rozwinięty gracz nawet jej nie
zauważy. To odwrócenie, nie skalowanie.

Zastąpiony typem **kruchym**, który daje pancernemu kontrast rytmiczny: raz coś
trwa długo, raz pęka natychmiast.

### Dlaczego boss zwęża się wolniej

Przy 4× HP i normalnym tempie zwężania boss byłby gwarantowanym zduszeniem, a
nie walką. Zwężanie 0,5× daje czas na starcie.

Gdy boss jednak zdusi piłkę, istniejąca kara (fala −1) cofa gracza poniżej progu
bossa, więc wraca do niego dopiero po odbudowaniu fali. Mechanika zduszenia
z kroku B1b sama obsługuje przegraną z bossem — nic dodatkowego nie trzeba.

## Dobór typu przy spawnie

Zwykły spawn bierze typy odblokowane na danej fali i losuje ważnie po
`effective_weight`.

Boss stoi obok tego mechanizmu, bo nie jest losowy. `RingField` pamięta, dla
której fali postawił już bossa; na fali podzielnej przez `BOSS_EVERY` (10)
pierwszy stawiany okrąg jest bossem, potem wraca zwykłe losowanie.

**Znacznik bossa kasuje się przy każdej zmianie fali**, w obie strony. Bez tego
powstaje pułapka: boss dusi piłkę na fali 10, kara cofa gracza na falę 9, gracz
odbudowuje falę 10 — a znacznik wciąż mówi „boss dla fali 10 już był" i gracz
mija bossa bez walki, na zawsze. `RingField` trzyma więc ostatnią widzianą falę
i czyści znacznik, gdy fala się zmieni.

`RingField` przyjmuje wstrzykiwany `random.Random`. Bez tego rozkład typów jest
nietestowalny, a to jedyna część projektu, w której błąd strojenia będzie
niewidoczny gołym okiem.

Sygnatury rozszerzają się o falę:

```python
field.update(dt, hp=..., wave=..., speed_multiplier=...)
field.spawn(hp, wave)
```

## Podział — własność `RingField`

`RingField.update()` sam wykrywa okręgi, które zginęły od ostatniego wywołania
i nie zostały jeszcze rozliczone (flaga `split_resolved`), i stawia dzieci.

Trzy konsekwencje tej decyzji:

- `main.py` nie dowiaduje się o istnieniu podziału — pętla główna zostaje cienka.
- Podział działa automatycznie **także przy zabiciu bombą**, która woła
  `target.destroy()` z zupełnie innego miejsca. Gdyby podział siedział w pętli
  kolizji, bomba by go nie wyzwalała.
- Okrąg nadal nie wie nic o polu — kierunek zależności zostaje nienaruszony.

Opóźnienie względem trafienia wynosi jeden krok fizyki (~4 ms), niewidoczne.

### Geometria podziału

Dzieci pojawiają się wewnątrz rodzica, na promieniach `R − 35`, `R − 70`
(odstęp `RING_GAP`), i muszą wypaść **powyżej** `ring_min_radius` — inaczej
dziecko zrodziłoby się od razu w stanie zduszenia. Jeśli miejsce starcza tylko
na jedno, powstaje jedno; jeśli na żadne, podziału nie ma i okrąg ginie
zwyczajnie. Dzieci są typu zwykłego.

Podział świadomie ignoruje limit `ring_max_active`: to jednorazowy wyskok, a
limit pilnuje tempa spawnu, nie sufitu absolutnego.

Znany skutek uboczny: piłka bywa po podziale **na zewnątrz** świeżego dziecka,
w pierścieniu między nim a rodzicem. To nie jest błąd — swept collision obsługuje
odbicie z obu stron, a taki moment jest właśnie tym „małym chaosem", po który
bierzemy ten typ.

## Nagrody

```python
def on_ring_destroyed(self, gold_multiplier=1.0, type_multiplier=1.0) -> float
```

Oba mnożniki działają niezależnie, więc złoty power-up na pancernym daje
7 × 2,5. `main.py` podaje `ring.type.coin_multiplier`.

**Boss nie daje kryształów.** Kryształy są walutą prestige'u, zdobywaną przez
prestige i osiągnięcia. Wypłata z bossa otworzyłaby drugie, niezależne źródło
waluty meta i rozregulowała ekonomię, której jeszcze nie stroiliśmy. Boss daje
8× monet i tyle.

**Skutek uboczny do świadomej akceptacji:** okrąg dzielący się to trzy zabicia
zamiast jednego, więc liczy się potrójnie do progu fali. Dzielące się pojawiają
się od fali 6, a fale i tak podnoszą trudność, więc efekt sam się hamuje.
Zapisane, żeby nie było niespodzianką przy strojeniu.

## Warstwa wizualna

- Kolor pochodzi z typu i wchodzi jako punkt „pełne HP" do istniejącej
  interpolacji ku czerwieni — mechanika zdrowia bez zmian.
- Grubość linii jest parametrem typu (boss grubszy).
- Nazwa typu pod paskiem HP dla wszystkiego poza zwykłym. Przy pięciu typach sam
  kolor byłby zagadką, a to gra oglądana, więc czytanie nie przeszkadza.
  Wymaga dorzucenia `font` do `CircleRing.draw()`; `main.py` ma go w zasięgu.

## Testowanie

Warstwa liczb, bez pygame (jak dotychczasowe 46 testów):

- waga efektywna i bramka `unlock_wave`,
- kadencja bossa: co 10 fal, raz na falę, ale **ponownie po powrocie na tę samą
  falę** (scenariusz: zduszenie przez bossa, spadek fali, odbudowa),
- rozkład typów na ustalonym ziarnie `random.Random`,
- geometria podziału: liczba dzieci, promienie, odmowa przy braku miejsca,
- jednorazowość podziału (flaga), podział po zabiciu bombą,
- mnożnik monet w `on_ring_destroyed`,
- mnożniki HP i zwężania zastosowane przy spawnie.

Dodatkowo **pomiar strojenia**: symulacja kilku fal z raportem, jaki procent
spawnów to który typ i jak długo każdy żyje. Przy limicie okręgów w B1a
dokładnie taki pomiar złapał błąd, którego 11 zielonych testów nie widziało —
rozkład ważony falą jest tej samej natury.

## Kroki implementacji

| Krok | Zakres | Widoczny efekt |
|---|---|---|
| B2a | `ring_types.py`, typ w `CircleRing`, spawn ważony, mnożnik monet | kolorowe okręgi o różnej wytrzymałości |
| B2b | podział: własność `RingField`, geometria, flaga jednorazowości | jeden okrąg staje się dwoma |
| B2c | boss: kadencja co 10 fal, wolniejsze zwężanie, oprawa | wydarzenie co dziesiątą falę |

Każdy krok z testami i osobnym commitem.

## Poza zakresem

- Sprawczość gracza (celowanie, popychanie piłki) — osobny cykl.
- Okrąg regenerujący — odrzucony, uzasadnienie wyżej.
- Kryształy z bossa — odrzucone, uzasadnienie wyżej.
- Odporność procentowa na obrażenia — bez sensu, dopóki `ball_damage` wynosi 1.
