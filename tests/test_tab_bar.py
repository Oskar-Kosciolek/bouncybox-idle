import re
from pathlib import Path

from ui.tab_bar import TabBar


def _dispatch_chains() -> list[set[int]]:
    """Łańcuchy `if/elif tab_bar.active == N` z main.py, każdy osobno.

    Rozdzielone po słowie kluczowym, nie po wcięciu: `if` otwiera nowy
    łańcuch, `elif` przedłuża bieżący. main.py ma ich dwa — jeden wybiera
    obsługę zdarzeń, drugi rysowanie — i każdy może się zestarzeć osobno.
    """
    src = (Path(__file__).resolve().parent.parent / "main.py"
           ).read_text(encoding="utf-8")

    chains: list[set[int]] = []
    for keyword, index in re.findall(
            r"\b(if|elif) tab_bar\.active == (\d+):", src):
        if keyword == "if":
            chains.append(set())
        chains[-1].add(int(index))
    return chains


def test_main_has_both_a_draw_chain_and_an_event_chain():
    """Suma obu łańcuchów potrafiła być kompletna, gdy jeden z nich gubił
    zakładkę — dlatego sprawdzamy je osobno, a najpierw że oba istnieją."""
    assert len(_dispatch_chains()) == 2


def test_every_dispatch_chain_covers_every_tab():
    """Dołożenie albo usunięcie zakładki przesuwa indeksy i po cichu
    podmienia widoki — klik w Prestiż otwierałby Osiagniecia, bez błędu."""
    expected = set(range(len(TabBar.TABS)))

    for i, chain in enumerate(_dispatch_chains()):
        assert chain == expected, f"lancuch {i}: brakuje {expected - chain}"
