"""Conferir consistência: o mesmo termo/texto traduzido igual no mod inteiro. Lógica pura, sem Tkinter.

Dois problemas:
- "divergente": o mesmo texto original aparece mais de uma vez com traduções diferentes;
- "glossario": o original tem um termo do glossário, mas a tradução não usa a forma do glossário.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .project import ATTENTION, IGNORED, PENDING


@dataclass
class Divergence:
    source: str
    versions: list[tuple[str, int]]  # (tradução, quantas vezes), a mais usada primeiro
    indexes: list[int] = field(default_factory=list)

    @property
    def best(self) -> str:
        return self.versions[0][0]


@dataclass
class GlossaryMiss:
    index: int
    term: str
    expected: str
    source: str


@dataclass
class Report:
    divergences: list[Divergence] = field(default_factory=list)
    misses: list[GlossaryMiss] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.divergences) + len(self.misses)


def _done(u) -> bool:
    return bool(u.translation.strip()) and u.status not in (PENDING, IGNORED)


def check(units, glossary=None) -> Report:
    rep = Report()
    by_src: dict[str, list[int]] = defaultdict(list)
    for i, u in enumerate(units):
        if _done(u) and u.source.strip():
            by_src[u.source].append(i)
    for src, idx in by_src.items():
        c = Counter(units[i].translation for i in idx)
        if len(c) > 1:
            rep.divergences.append(Divergence(src, c.most_common(), idx))
    if glossary is not None and glossary.terms:
        for i, u in enumerate(units):
            if not _done(u):
                continue
            for _s, _e, final in glossary.find(u.source):
                if final not in u.translation:
                    rep.misses.append(GlossaryMiss(i, u.source[_s:_e], final, u.source))
                    break  # um aviso por texto basta
    rep.divergences.sort(key=lambda d: -sum(n for _t, n in d.versions))
    return rep


def unify(units, divergence: Divergence) -> int:
    """Troca as versões menos usadas pela mais usada. Devolve quantos textos mudaram."""
    n = 0
    for i in divergence.indexes:
        if units[i].translation != divergence.best:
            units[i].translation = divergence.best
            n += 1
    return n


def mark_for_review(units, misses) -> int:
    n = 0
    for m in misses:
        u = units[m.index]
        if u.status != ATTENTION:
            u.status = ATTENTION
            u.note = f"Glossário: “{m.term}” deveria aparecer como “{m.expected}”."
            n += 1
    return n


def glossary_usage(units, glossary) -> tuple[int, int]:
    """(textos traduzidos que usam o glossário, textos traduzidos que tinham um termo do glossário mas não o usaram)."""
    if glossary is None or not glossary.terms:
        return 0, 0
    used = missed = 0
    for u in units:
        if not _done(u):
            continue
        hits = glossary.find(u.source)
        if not hits:
            continue
        if all(final in u.translation for _s, _e, final in hits):
            used += 1
        else:
            missed += 1
    return used, missed
