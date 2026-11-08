"""Sugestão de presets de glossário e lista de nomes novos do mod (sem janela; testado em tests/test_tools.py)."""
from __future__ import annotations

import re
from typing import Iterable


def _compile(terms: Iterable[str]) -> re.Pattern | None:
    ts = sorted({t for t in terms if t and len(t) >= 3}, key=len, reverse=True)
    if not ts:
        return None
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in ts) + r")(?![\w])")


def suggest_presets(sources: list[str], presets: dict[str, dict], min_hits: int = 3) -> list[dict]:
    """
    sources: textos originais do mod. presets: {id: {"nome":..., "terms": {termo_en: traducao}}}.
    Devolve [{id, nome, hits, exemplos}] dos presets cujo(s) termo(s) aparecem >= min_hits vezes, do mais ao menos usado.
    """
    text = "\n".join(sources)
    out = []
    for pid, p in presets.items():
        rx = _compile(p.get("terms", {}).keys())
        if rx is None:
            continue
        found: dict[str, int] = {}
        for m in rx.finditer(text):
            found[m.group(1)] = found.get(m.group(1), 0) + 1
        hits = sum(found.values())
        if hits >= min_hits:
            ex = sorted(found, key=lambda k: -found[k])[:5]
            out.append({"id": pid, "nome": p.get("nome", pid), "hits": hits, "termos": len(found), "exemplos": ex})
    return sorted(out, key=lambda d: -d["hits"])


_NAME = re.compile(r"^[A-ZÀ-Þ][\w'’.-]*(?: [\w'’.-]+){0,4}$")


def new_names(units, known: Iterable[str], limit: int = 200) -> list[str]:
    """
    Nomes de registros do mod (campo vazio = nome do registro) que não estão no glossário nem nos presets.
    São os candidatos a nome próprio novo: decida se mantém ou traduz ANTES de traduzir o mod.
    """
    k = {x.casefold() for x in known}
    seen: dict[str, int] = {}
    for u in units:
        if u.field:
            continue
        s = (u.source or "").strip()
        if not (2 <= len(s) <= 40) or s.casefold() in k or not _NAME.match(s) or "/" in s:
            continue
        seen[s] = seen.get(s, 0) + 1
    return sorted(seen)[:limit]
