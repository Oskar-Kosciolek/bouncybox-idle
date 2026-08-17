"""Odsłuch barw muzycznych — uruchamiany ręcznie, nie jest testem.

Gra kilkanaście sekund generatywnej melodii każdą dostępną barwą, żeby dało
się je porównać uchem. Wybór barwy to decyzja słuchowa, której nie da się
rozstrzygnąć pomiarem.

Uruchomienie:
    ./.venv/Scripts/python.exe tools/preview_music.py
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from audio import Audio  # noqa: E402
from music import TIMBRES, Music  # noqa: E402

SECONDS_PER_TIMBRE = 14.0
STEP = 1 / 60


def preview(name: str) -> None:
    print(f"\n  >>> {name}")
    music = Music(volume=0.5, rng=random.Random(11), timbre=name)
    if not music.available:
        print("      (mikser niedostepny)")
        return

    elapsed = 0.0
    while elapsed < SECONDS_PER_TIMBRE:
        # Napięcie rośnie w trakcie próbki, żeby słychać było reakcję na grę
        tension = min(1.0, elapsed / SECONDS_PER_TIMBRE)
        music.update(STEP, wave=6, tension=tension)
        time.sleep(STEP)
        elapsed += STEP

    time.sleep(1.5)   # niech ostatnia nuta wybrzmi


if __name__ == "__main__":
    pygame.init()
    Audio()           # otwiera mikser, z którego korzysta Music
    print("Odsluch barw. Kazda gra ~14 s, napiecie rosnie od zera do maksimum.")
    for timbre in TIMBRES:
        preview(timbre)
    print("\nGotowe.")
    pygame.quit()
