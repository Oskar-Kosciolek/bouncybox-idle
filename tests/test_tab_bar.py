import re
from pathlib import Path

from ui.tab_bar import TabBar


def test_main_dispatches_every_tab_that_the_bar_shows():
    """main.py wybiera widok łańcuchem `tab_bar.active == N`. Dołożenie albo
    usunięcie zakładki przesuwa indeksy i po cichu podmienia widoki — klik
    w Prestiż otwierałby Osiagniecia, bez błędu i bez śladu w testach.
    """
    src = (Path(__file__).resolve().parent.parent / "main.py"
           ).read_text(encoding="utf-8")

    handled = {int(n) for n in re.findall(r"tab_bar\.active == (\d+)", src)}

    # Zakładka 0 (Gra) to sam HUD — nie ma panelu, więc main.py jej nie łapie.
    assert handled == set(range(1, len(TabBar.TABS)))
