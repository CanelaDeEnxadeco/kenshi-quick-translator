"""Confere se os textos traduzidos usam só caracteres que a fonte do Kenshi desenha (sem janela; testado)."""
from __future__ import annotations

import re
from collections import Counter

# Faixa usada pelo pacote de idioma pt-BR do Kenshi (kenshi_fonts.xml: <Code range="32 255"/>).
DEFAULT_RANGES = ((32, 255),)

# Pontuação "bonita" que tradutores automáticos adoram e que a fonte não tem: vira o equivalente simples.
TYPO = {
    "‘": "'", "’": "'", "‚": ",", "‛": "'",
    "“": '"', "”": '"', "„": '"', "″": '"', "′": "'",
    "–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-",
    "…": "...", "•": "*", " ": " ", "​": "", "‎": "", "‏": "", "﻿": "",
    "→": "->", "←": "<-", "✓": "v", "×": "x",
}


def parse_ranges(xml_text: str) -> tuple[tuple[int, int], ...]:
    """Lê <Code range="a b"/> de um kenshi_fonts.xml. Vazio -> faixa padrão."""
    found = [(int(a), int(b)) for a, b in re.findall(r'<Code\s+range="(\d+)\s+(\d+)"', xml_text)]
    if not found:
        return DEFAULT_RANGES
    # a menor cobertura entre as fontes é a que vale para o pior caso
    lo = max(a for a, _ in found)
    hi = min(b for _, b in found)
    return ((min(a for a, _ in found), hi),) if hi >= lo else tuple(found)


def ok_char(ch: str, ranges=DEFAULT_RANGES) -> bool:
    if ch in "\n\r\t":
        return True
    o = ord(ch)
    return any(a <= o <= b for a, b in ranges)


def scan(units, ranges=DEFAULT_RANGES) -> dict:
    """{'chars': Counter, 'units': [(string_id, field, [caracteres])]} só das traduções com problema."""
    chars: Counter = Counter()
    bad_units = []
    for u in units:
        t = u.translation or ""
        bad = [c for c in t if not ok_char(c, ranges)]
        if bad:
            chars.update(bad)
            bad_units.append((u.string_id, u.field, sorted(set(bad))))
    return {"chars": chars, "units": bad_units}


def fix_typography(units, ranges=DEFAULT_RANGES) -> tuple[int, Counter]:
    """Troca a pontuação bonita pelo equivalente simples. Devolve (textos alterados, caracteres que ficaram sem solução)."""
    changed = 0
    left: Counter = Counter()
    for u in units:
        t = u.translation or ""
        if not t:
            continue
        new = "".join(TYPO[c] if c in TYPO and not ok_char(c, ranges) else c for c in t)
        if new != t:
            u.translation = new
            changed += 1
        left.update(c for c in new if not ok_char(c, ranges))
    return changed, left
