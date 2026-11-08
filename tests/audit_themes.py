"""Contraste (WCAG) dos pares texto/fundo de cada tema. Uso: python tests/audit_themes.py  (precisa tkinter importável)"""
import sys
sys.path.insert(0, ".")
from kenshi_quick_translator import gui  # noqa: E402  (rode com o Python que tem tkinter)


def lum(c):
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


PAIRS = [("INK", "BG", 7), ("INK", "CARD", 7), ("MUTED", "CARD", 4.5), ("white", "ACCENT", 4.5), ("white", "GREEN", 3),
         ("white", "RED", 3), ("INK", "BTN", 7), ("INK", "DONE", 7), ("INK", "PART", 7), ("INK", "ATT", 7), ("INK", "REV", 7),
         ("WARN", "ATT", 4.5), ("OKFG", "DONE", 4.5), ("IGN", "CARD", 3), ("white", "ACC_ACT", 4.5), ("HEADSUB", "HEAD", 4.5)]
bad = 0
for name, pal in gui.PALETTES.items():
    for fg, bg, need in PAIRS:
        a = "#ffffff" if fg == "white" else pal[fg]
        r = ratio(a, pal[bg])
        if r < need:
            bad += 1
            print(f"{name:9} {fg:8} em {bg:8} {r:4.1f} (< {need})")
print("falhas:", bad)
