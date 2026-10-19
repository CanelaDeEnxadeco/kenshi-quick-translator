"""
Ajudas da tela de revisão. Sem Tkinter e sem toolkit: tudo aqui é lógica pura e testável.

- itens duvidosos (contador);
- diferença de marcadores /XXX/ entre original e tradução, com posições para colorir;
- desfazer a edição de um texto;
- idioma de origem de cada texto (filtro da tabela).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .markers import MARKER_RE

ATTENTION = "atencao"
AUTO = "automatica"
IGNORED = "ignorada"


# ---------------------------------------------------------------- marcadores
@dataclass
class MarkerDiff:
    missing: list[str] = field(default_factory=list)  # estão no original e sumiram da tradução
    extra: list[str] = field(default_factory=list)  # estão na tradução e não existem no original
    spans: list[tuple[int, int, bool]] = field(default_factory=list)  # (início, fim, bate?) na TRADUÇÃO

    @property
    def ok(self) -> bool:
        return not self.missing and not self.extra


def marker_diff(source: str, translation: str) -> MarkerDiff:
    """Compara os marcadores. Tradução vazia = o original será mantido: não há o que acusar."""
    if not translation.strip():
        return MarkerDiff()
    want, got = Counter(MARKER_RE.findall(source)), Counter(MARKER_RE.findall(translation))
    diff = MarkerDiff(missing=sorted((want - got).elements()), extra=sorted((got - want).elements()))
    left = Counter(want)
    for m in MARKER_RE.finditer(translation):
        good = left[m.group()] > 0
        if good:
            left[m.group()] -= 1
        diff.spans.append((m.start(), m.end(), good))
    return diff


def marker_spans_source(source: str) -> list[tuple[int, int]]:
    """Posições dos marcadores no original (para realçar o que precisa existir na tradução)."""
    return [(m.start(), m.end()) for m in MARKER_RE.finditer(source)]


# ---------------------------------------------------------------- duvidosos
@dataclass
class Doubtful:
    attention: int = 0  # estado "Conferir"
    broken_markers: int = 0  # tem tradução, mas os marcadores não batem
    same_as_source: int = 0  # "traduzida" automaticamente, mas igual ao original

    @property
    def total(self) -> int:
        return self.attention + self.broken_markers + self.same_as_source


def reason(unit) -> str:
    """'' se está tudo bem; senão 'atencao' | 'marcadores' | 'igual'."""
    if unit.status == ATTENTION:
        return "atencao"
    if unit.status == IGNORED:
        return ""
    if unit.translation.strip() and not marker_diff(unit.source, unit.translation).ok:
        return "marcadores"
    if (unit.status == AUTO and unit.translation.strip() == unit.source.strip()
            and sum(c.isalpha() for c in unit.source) >= 4):
        return "igual"
    return ""


def doubtful_indexes(units) -> list[int]:
    return [i for i, u in enumerate(units) if reason(u)]


def count_doubtful(units) -> Doubtful:
    d = Doubtful()
    for u in units:
        r = reason(u)
        if r == "atencao":
            d.attention += 1
        elif r == "marcadores":
            d.broken_markers += 1
        elif r == "igual":
            d.same_as_source += 1
    return d


# ---------------------------------------------------------------- desfazer
@dataclass
class _Snap:
    key: tuple[str, str]
    translation: str
    status: str
    note: str


class UndoHistory:
    """Pilha de edições manuais: cada edição guarda o estado de ANTES. Só vale na sessão aberta."""

    def __init__(self, limit: int = 200) -> None:
        self.limit = limit
        self._stack: list[_Snap] = []

    def push(self, unit) -> None:
        self._stack.append(_Snap(unit.key, unit.translation, unit.status, unit.note))
        del self._stack[: -self.limit]

    def clear(self) -> None:
        self._stack.clear()

    def __len__(self) -> int:
        return len(self._stack)

    def peek_key(self) -> tuple[str, str] | None:
        return self._stack[-1].key if self._stack else None

    def pop(self, units) -> int | None:
        """Desfaz a última edição; devolve a posição da unidade na lista (ou None se não dá)."""
        while self._stack:
            snap = self._stack.pop()
            for i, u in enumerate(units):
                if u.key == snap.key:
                    u.translation, u.status, u.note = snap.translation, snap.status, snap.note
                    return i
        return None


# ---------------------------------------------------------------- idioma de origem
def source_languages(units) -> dict[str, int]:
    """Quantos textos há por idioma detectado (só no modo "vários idiomas"; vazio caso contrário)."""
    out: dict[str, int] = {}
    for u in units:
        if u.lang:
            out[u.lang] = out.get(u.lang, 0) + 1
    return out
