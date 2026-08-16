"""Skrócony zapis dużych liczb na potrzeby HUD i sklepu.

Ujście dla monet jest nieograniczone, więc kwoty rosną bez sufitu. Pełny zapis
(`3,494,541`) nie mieści się w pasku HUD ani w wierszu sklepu, a przy miliardach
przestaje być czytelny nawet gdyby się mieścił.
"""

_SUFFIXES = ("K", "M", "B", "T")


def short_number(value: float) -> str:
    """Zwraca liczbę w zapisie 742 / 1.2K / 123K / 3.4M / 5.00e+18.

    Trzy cyfry znaczące: poniżej 100 z częścią dziesiętną, powyżej bez —
    dziesiąta część przy 123K i tak nic nie wnosi, a zabiera miejsce.
    """
    sign = "-" if value < 0 else ""
    magnitude = abs(value)

    if round(magnitude) < 1000:
        return f"{sign}{magnitude:.0f}"

    # Progi to 99.95 i 999.5, a nie 100 i 1000: liczy się to, co wyjdzie PO
    # zaokrągleniu do wyświetlanej precyzji. Inaczej 999600 pokazałoby się
    # jako "1000K" — cztery cyfry tam, gdzie przyrostek ma ich oszczędzić.
    scaled = magnitude
    for suffix in _SUFFIXES:
        scaled /= 1000.0
        if scaled < 99.95:
            return f"{sign}{scaled:.1f}{suffix}"
        if scaled < 999.5:
            return f"{sign}{scaled:.0f}{suffix}"

    # Poza tabelą przyrostków — notacja naukowa z oryginalnej wartości,
    # nie z przeskalowanej resztki po pętli
    return f"{sign}{magnitude:.2e}"
