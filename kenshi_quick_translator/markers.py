"""
Proteção do que não pode ser traduzido dentro de um texto.

O Kenshi troca marcadores como /TEAMUP/ ou /BROTHER/ por palavras na hora
do jogo (a sintaxe exige as duas barras e aceita sufixo colado, como em
/BASTARD/s). Um tradutor automático que mexa neles deixa lixo na tela do
jogo, sem nenhum erro visível. Aqui o texto é "mascarado" antes de ir ao
serviço de tradução e restaurado depois, com validação de que nada se perdeu.

Também mascara termos do glossário, para que saiam sempre com a tradução
escolhida pelo usuário (ou fiquem intactos).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from .glossary import Glossary

# /TEAMUP/, /BROTHER/, /GETLOST/ ... sempre maiúsculas, com as duas barras.
MARKER_RE = re.compile(r"/[A-Z0-9_]{2,}/")

STYLES = ("alnum", "tag")


@dataclass
class Piece:
    """Um pedaço do texto: traduzível ('text') ou fixo ('fixed')."""

    kind: str  # 'text' | 'fixed'
    value: str


@dataclass
class Masked:
    """Texto pronto para enviar ao tradutor, com o necessário para restaurar."""

    source: str
    pieces: list[Piece] = field(default_factory=list)

    @property
    def fixed(self) -> list[str]:
        return [p.value for p in self.pieces if p.kind == "fixed"]

    @property
    def has_fixed(self) -> bool:
        return any(p.kind == "fixed" for p in self.pieces)

    def text_for(self, style: str = "alnum") -> str:
        """Texto com os trechos fixos trocados por fichas que o tradutor respeita."""
        out: list[str] = []
        n = 0
        for p in self.pieces:
            if p.kind == "text":
                out.append(p.value)
            else:
                out.append(_token(n, style))
                n += 1
        return "".join(out)

    def restore(self, translated: str, style: str = "alnum") -> tuple[str, list[str]]:
        """
        Devolve (texto restaurado, problemas). Lista de problemas vazia = ok.
        """
        problems: list[str] = []
        fixed = self.fixed
        pattern = _restore_re(style)
        seen: Counter[int] = Counter()

        def sub(m: re.Match[str]) -> str:
            idx = int(m.group(1))
            seen[idx] += 1
            if idx >= len(fixed):
                problems.append(f"ficha inesperada {m.group(0)!r}")
                return ""
            return fixed[idx]

        restored = pattern.sub(sub, translated)

        for i, original in enumerate(fixed):
            if seen[i] == 0:
                problems.append(f"sumiu: {original}")
            elif seen[i] > 1:
                problems.append(f"repetido: {original}")

        # Conferência final: os marcadores do jogo têm de ser exatamente os mesmos.
        if Counter(MARKER_RE.findall(self.source)) != Counter(MARKER_RE.findall(restored)):
            if not problems:
                problems.append("marcadores diferentes do original")
        return restored, problems

    def text_pieces(self) -> list[str]:
        return [p.value for p in self.pieces if p.kind == "text"]

    def join_pieces(self, translated_texts: Iterable[str]) -> str:
        """Remonta o texto com cada trecho traduzível já traduzido separadamente."""
        it = iter(translated_texts)
        out: list[str] = []
        for p in self.pieces:
            out.append(next(it) if p.kind == "text" else p.value)
        return "".join(out)


def _token(n: int, style: str) -> str:
    if style == "tag":
        return f"<x{n}/>"
    return f"ZQ{n}ZQ"


def _restore_re(style: str) -> re.Pattern[str]:
    if style == "tag":
        return re.compile(r"<\s*x\s*(\d+)\s*/\s*>", re.IGNORECASE)
    return re.compile(r"ZQ\s*(\d+)\s*ZQ", re.IGNORECASE)


def mask(
    text: str,
    glossary: Glossary | None = None,
    extra_patterns: Iterable[str] = (),
) -> Masked:
    """Separa o texto em pedaços traduzíveis e pedaços que devem ficar fixos."""
    spans: list[tuple[int, int, str]] = []  # (inicio, fim, valor final)

    for m in MARKER_RE.finditer(text):
        spans.append((m.start(), m.end(), m.group(0)))
    for pat in extra_patterns:
        for m in re.finditer(pat, text):
            if m.end() > m.start():
                spans.append((m.start(), m.end(), m.group(0)))
    if glossary is not None:
        for start, end, repl in glossary.find(text):
            spans.append((start, end, repl))

    # Sem sobreposição: o que começa antes e é mais longo vence.
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    chosen: list[tuple[int, int, str]] = []
    last_end = 0
    for s in spans:
        if s[0] >= last_end:
            chosen.append(s)
            last_end = s[1]

    pieces: list[Piece] = []
    pos = 0
    for start, end, value in chosen:
        if start > pos:
            pieces.append(Piece("text", text[pos:start]))
        pieces.append(Piece("fixed", value))
        pos = end
    if pos < len(text):
        pieces.append(Piece("text", text[pos:]))
    return Masked(source=text, pieces=pieces)


def count_markers(text: str) -> Counter[str]:
    return Counter(MARKER_RE.findall(text))


def markers_match(source: str, translation: str) -> bool:
    """True se a tradução tem exatamente os mesmos marcadores do original."""
    return count_markers(source) == count_markers(translation)


def has_letters(text: str) -> bool:
    return any(c.isalpha() for c in text)
