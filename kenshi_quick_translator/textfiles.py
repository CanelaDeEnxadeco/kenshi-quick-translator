"""
Arquivos de texto soltos na pasta do mod (ex.: tips.txt, as dicas da tela de carregamento).

Só entram arquivos .txt na raiz da pasta cujo conteúdo parece FRASES (uma por linha). Listas de
nomes (namesF.txt, namesM.txt...) têm 2 palavras por linha e ficam como estão: traduzir nomes
inventados só os estragaria. Cada linha é traduzida com a mesma proteção de códigos, glossário e
memória de tradução do resto do programa; se o serviço falhar numa linha, ela fica no original.
"""
from __future__ import annotations

import statistics
import threading
from pathlib import Path

from .core import _keep_edges, _run_chunk
from .markers import has_letters, mask
from .providers import ProviderError

MAX_BYTES = 1_000_000
MIN_LINES = 3
MIN_MEDIAN_WORDS = 4  # lista de nomes: ~2; dicas e frases: bem mais


def _decode(raw: bytes) -> tuple[str, str] | None:
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"  # mantém a marca BOM só se já tinha
    try:
        return raw.decode(enc), enc
    except UnicodeDecodeError:
        return None


def is_sentence_file(text: str) -> bool:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < MIN_LINES:
        return False
    return statistics.median(len(l.split()) for l in lines) >= MIN_MEDIAN_WORDS


def find_text_files(folder: str | Path | None) -> list[Path]:
    """.txt da raiz da pasta do mod que parecem frases (não nomes)."""
    out: list[Path] = []
    if folder is None or not Path(folder).is_dir():
        return out
    for f in sorted(Path(folder).glob("*.txt")):
        try:
            if f.stat().st_size > MAX_BYTES:
                continue
            dec = _decode(f.read_bytes())
        except OSError:
            continue
        if dec and is_sentence_file(dec[0]):
            out.append(f)
    return out


def translate_strings(
    strings: list[str], provider, target: str, source: str = "auto", glossary=None, memory=None,
    cancel: threading.Event | None = None, progress=None, label: str = "",
) -> dict[str, str]:
    """
    Traduz textos soltos (uma frase por item) com a mesma proteção de códigos, glossário e memória
    do resto do programa. Devolve {original: tradução}; o que o serviço não traduziu fica de fora.
    """
    cancel = cancel or threading.Event()
    uniq = list(dict.fromkeys(l.strip() for l in strings if has_letters(l)))
    done: dict[str, str] = {}
    if memory:
        for s, t in memory.get_many(set(uniq), target).items():
            if t:
                done[s] = t
    todo = [s for s in uniq if s not in done]
    size = max(1, getattr(provider, "max_batch", 10) or 10)
    for i in range(0, len(todo), size):
        if cancel.is_set():
            break
        chunk = todo[i : i + size]
        masked = {s: mask(s, glossary) for s in chunk}
        try:
            res = _run_chunk(provider, chunk, masked, source, target, cancel)
        except ProviderError:
            continue  # essas linhas ficam no original
        new = [(s, r[0]) for s, r in res.items() if r[0] is not None and r[1] == "automatica"]
        done.update(new)
        if memory and new:
            memory.put_many(new, target, origin=getattr(provider, "name", ""))
        if progress:
            progress(label, min(i + size, len(todo)), len(todo))
    return done


def translate_text_files(
    files: list[Path], provider, target: str, source: str = "auto", glossary=None, memory=None,
    cancel: threading.Event | None = None, progress=None,
) -> dict[str, bytes]:
    """Devolve {nome do arquivo: conteúdo traduzido (bytes)}. Linhas sem tradução ficam no original."""
    out: dict[str, bytes] = {}
    for f in files:
        raw = f.read_bytes()
        dec = _decode(raw)
        if dec is None:
            continue
        text, enc = dec
        lines = text.split("\n")
        cr = [l.endswith("\r") for l in lines]
        body = [l[:-1] if l.endswith("\r") else l for l in lines]
        done = translate_strings(body, provider, target, source, glossary, memory, cancel, progress, f.name)
        result = []
        for l, c in zip(body, cr):
            t = done.get(l.strip())
            result.append((_keep_edges(l, t) if t else l) + ("\r" if c else ""))
        out[f.name] = "\n".join(result).encode(enc)
    return out
