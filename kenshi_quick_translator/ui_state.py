"""Lógica da janela que não depende do Tkinter (por isso dá para testar): tamanho da letra e posição salva."""
from __future__ import annotations

import re

FONT_STEPS = (85, 100, 115, 130, 150)  # % do tamanho normal da letra
NARROW_WIDTH = 1240  # abaixo disso a lista de mods vira uma gaveta
_GEO = re.compile(r"^(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)$")


def clamp_scale(value) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 100
    return max(70, min(200, v))


def step_font(current, direction: int) -> int:
    """Próximo tamanho da lista FONT_STEPS (direction +1/-1); 0 volta ao normal (100)."""
    if direction == 0:
        return 100
    cur = clamp_scale(current)
    if direction > 0:
        return next((s for s in FONT_STEPS if s > cur), FONT_STEPS[-1])
    return next((s for s in reversed(FONT_STEPS) if s < cur), FONT_STEPS[0])


def parse_geometry(geo: str) -> tuple[int, int, int, int] | None:
    """'1200x800+10+20' (ou com '+-8') -> (largura, altura, x, y); None se não for uma geometria válida."""
    m = _GEO.match((geo or "").strip())
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    x, y = int(m.group(3).replace("+", "")), int(m.group(4).replace("+", ""))
    return w, h, x, y


def clamp_geometry(geo: str, virtual: tuple[int, int, int, int], minsize: tuple[int, int]) -> str | None:
    """
    Garante que a posição salva ainda cabe na tela (ex.: o segundo monitor foi desligado).
    virtual = (x, y, largura, altura) da área de trabalho; devolve a geometria corrigida ou None se a salva for inválida.
    """
    parsed = parse_geometry(geo)
    if parsed is None:
        return None
    w, h, x, y = parsed
    vx, vy, vw, vh = virtual
    w = max(minsize[0], min(w, vw - 20))
    h = max(minsize[1], min(h, vh - 60))
    x = max(vx, min(x, vx + vw - w))
    y = max(vy, min(y, vy + vh - h - 40))  # deixa espaço para a barra de tarefas
    return f"{w}x{h}+{x}+{y}"
