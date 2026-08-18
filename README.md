# bouncybox idle

Gra idle, w której piłka odbija się wewnątrz współśrodkowych okręgów. Okręgi
kurczą się w stronę środka, a gdy najbardziej wewnętrzny dociśnie piłkę do
minimum i przetrzyma tam przez chwilę karencji, runda kończy się utratą fali.
Zniszczone okręgi płacą monetami, monety kupują ulepszenia, ulepszenia
pozwalają niszczyć szybciej — i tak w kółko. Gra liczy zarobek także wtedy,
gdy jest zamknięta.

Napisana w Pythonie na pygame-ce. Bez plików graficznych i dźwiękowych: cała
oprawa, łącznie z efektami i muzyką, powstaje proceduralnie w kodzie.

## Uruchomienie

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python.exe main.py
```

Okno startuje w rozmiarze 700x520 i można je swobodnie skalować. Przy niskim
oknie panel po prawej robi się ciasny — drzewko ulepszeń przewija się wtedy
kółkiem myszy.

## Jak się gra

Piłka porusza się sama; gracz nie celuje. Wpływ ma przez zakupy, a nie przez
refleks.

**Dwie drogi zniszczenia okręgu.** Odbicie od litej części zdejmuje tyle HP,
ile wynosi siła uderzenia piłki. Przelot przez dziurę zadaje wielokrotność tej
wartości — dziura jest drogą szybką, ale zależy od szczęścia, bo piłka nie
wybiera, gdzie trafi. Obie drogi zależą od tego samego ulepszenia obrażeń,
więc się mnożą, zamiast konkurować.

**Zagrożenie.** Okręgi zwężają się z czasem, a tempo rośnie z falą (do
sufitu, żeby wysokie fale nie zamieniły się w loterię). Okrąg dociśnięty do
minimalnego promienia daje jeszcze kilka sekund karencji — przy tak ciasnym
okręgu piłka odbija się kilka razy na sekundę, więc to realna szansa na
dobicie. Gdy karencja minie, plansza czyści się, fala spada o jeden, a monety
i ulepszenia zostają.

**Typy okręgów.** Poza zwykłym pojawiają się kruchy, pancerny, dzielący się na
mniejsze oraz boss co dziesiątą falę. Skład planszy przesuwa się z falami:
typy specjalne stopniowo wypierają zwykły.

**Prestige** odblokowuje się od fali 10. Resetuje monety i ulepszenia, ale daje
kryształy na ulepszenia permanentne.

**Postęp offline** nalicza się do ośmiu godzin nieobecności, w tempie około
jednej trzeciej zarobku w trakcie grania (dwukrotnie więcej z auto-kolektorem).

## Sterowanie

Panel po prawej ma sześć zakładek: **Gra**, **Sklep**, **Drzewko**,
**Prestige**, **Osiągnięcia**, **Ustawienia**. Ulepszenia da się kupować
zarówno w Sklepie, jak i klikając węzły w Drzewku.

| Klawisz | Działanie |
|---|---|
| `ESC` | zapis i wyjście |
| `R` | nowa runda — zachowuje monety, ulepszenia i falę |
| `F5` | ręczny zapis |
| `F6` | kasuje zapis i zaczyna od zera |

Gra zapisuje się sama co 30 sekund do `save.json` obok plików gry.

## Struktura kodu

| Warstwa | Pliki | Zależność od pygame |
|---|---|---|
| Stan i ekonomia | `game_state.py`, `upgrade_tree.py`, `achievements.py`, `ring_types.py`, `config.py` | **żadna** |
| Symulacja | `ball.py`, `circle_ring.py`, `ring_field.py`, `powerup.py`, `particles.py`, `timestep.py` | tylko rysowanie |
| Oprawa | `audio.py`, `music.py`, `formatting.py` | mikser i powierzchnie |
| Interfejs | `ui/` | pełna |
| Orkiestracja | `main.py` | pętla gry |

Trzy rzeczy warte uwagi przed pierwszą zmianą:

**`Config` dzieli pola na strojone i pochodne.** `apply_upgrades` przelicza
pochodne od stałych `BASE_*` przy każdym zakupie, awansie fali i wczytaniu
zapisu. Wpisanie wartości wprost w pole pochodne nie przetrwa najbliższego
zakupu — trzeba zmieniać jego *wejście*. Testy pilnują, żeby żaden suwak nie
celował w pole pochodne.

**Fizyka chodzi stałym krokiem** (`timestep.py`), niezależnym od liczby klatek.
Kolizje sprawdzają odcinek ruchu piłki, nie jej bieżącą pozycję, więc szybka
piłka nie przelatuje przez okrąg.

**Zapis jest atomowy i tolerancyjny.** Idzie przez plik tymczasowy, niesie
numer wersji, pomija nieznane pola i uzupełnia brakujące wartościami
domyślnymi — dodanie lub usunięcie pola w `GameState` nie unieważnia zapisów.

## Testy

```bash
.venv/Scripts/python.exe -m pytest -q
```

**Żaden test nie potrzebuje okna gry.** To nie ciekawostka, tylko własność, na
której stoi cała reszta: ekonomię, balans i logikę pola okręgów da się
sprawdzić w milisekundach, a testy rysowania korzystają z `pygame.Surface`
i `pygame.font.init()`, które działają bez `set_mode`. Zestaw uruchamia się
w sekundę, więc opłaca się go uruchamiać po każdej zmianie.

## Strojenie i narzędzia

Zakładka **Ustawienia** to panel deweloperski z suwakami: karencja zduszenia,
mnożnik obrażeń dziury, tempo i sufit zwężania, promienie, głośność efektów
i muzyki. Zmiany działają od razu.

```bash
.venv/Scripts/python.exe tools/measure_ring_types.py   # rozklad typow, tempo, zduszenia
.venv/Scripts/python.exe tools/preview_music.py        # odsluch barw muzycznych
```

Skrypt pomiarowy istnieje z konkretnego powodu: testy jednostkowe sprawdzają,
czy pojedyncza reguła działa, ale nie odpowiadają na pytanie, do czego zbiór
reguł prowadzi po kilkunastu minutach gry. Dwa razy w historii tego projektu
zielony zestaw testów przepuścił błąd, który pomiar wychwycił od razu.

## Dokumentacja projektowa

`docs/superpowers/specs/` i `docs/superpowers/plans/` zawierają specyfikację
i plan wdrożenia systemu typów okręgów — z uzasadnieniami decyzji, w tym tych
odrzuconych.
