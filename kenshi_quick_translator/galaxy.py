"""
Temas com efeito (Azul galáxia, Verde, Vermelho, Amarelo, Laranja, Roxo, Rosa): faixa do topo com degradê brilhando de baixo para cima e pontos de luz
(vagalumes) planando devagar. Só usa o Tkinter (sem Pillow). Tkinter não tem transparência, então
o efeito vive nesta faixa; o resto da janela só usa as cores do tema.
"""
from __future__ import annotations

import math
import random
import tkinter as tk

import colorsys

FPS_MS = 45               # um quadro a cada 45 ms (~22 por segundo)

# matiz (0-360) de cada tema com efeito; "galaxia" é o azul
HUES = {"galaxia": 226, "verde": 138, "vermelho": 355, "amarelo": 46, "laranja": 24, "roxo": 272, "rosa": 328}
THEME_NAMES = {
    "galaxia": "Azul galáxia", "verde": "Verde", "vermelho": "Vermelho", "amarelo": "Amarelo",
    "laranja": "Laranja", "roxo": "Roxo", "rosa": "Rosa",
}


def _rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, s, v)
    return (round(r * 255), round(g * 255), round(b * 255))


def fx_colors(theme: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """(topo escuro, brilho de baixo, cor das luzes) do tema."""
    h = HUES.get(theme, 226)
    glow_v = 1.0 if h in (46, 24, 138) else 0.95
    return _rgb(h, 0.75, 0.11), _rgb(h, 0.85 if h != 46 else 0.9, glow_v), _rgb(h, 0.32, 1.0)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


def _hex(c: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % c


def gradient_color(y: int, height: int, base=None, glow=None) -> tuple[int, int, int]:
    """Cor do fundo na altura y: escuro no topo, brilho colorido embaixo (cresce de forma suave)."""
    b0, g0, _ = fx_colors("galaxia")
    t = y / max(1, height - 1)
    return _mix(base or b0, glow or g0, (t ** 2.4) * 0.95)


class GalaxyBanner(tk.Canvas):
    def __init__(self, parent: tk.Misc, title: str, subtitle: str, title_font, sub_font, height: int = 86,
                 theme: str = "galaxia") -> None:
        self._base, self._glow, self._light = fx_colors(theme)
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=_hex(self._base))
        self._h = height
        self._cw = 0
        self._img: tk.PhotoImage | None = None
        self._flies: list[dict] = []
        self._job: str | None = None
        self._tick = 0
        self._title, self._subtitle = title, subtitle
        self._tf, self._sf = title_font, sub_font
        self.bind("<Configure>", self._on_resize)
        self.bind("<Destroy>", lambda _e: self.stop(), add="+")
        self.start()

    # ---- desenho
    def _on_resize(self, e: tk.Event) -> None:
        if abs(e.width - self._cw) < 2 or e.width < 10:
            return
        self._cw = e.width
        self._paint()

    def _paint(self) -> None:
        w, h = self._cw, self._h
        self.delete("all")
        img = tk.PhotoImage(width=w, height=h)
        for y in range(h):
            img.put(_hex(gradient_color(y, h, self._base, self._glow)), to=(0, y, w, y + 1))
        self._img = img  # o Tk não guarda a imagem sozinho
        self.create_image(0, 0, image=img, anchor="nw")
        self.create_text(22, h // 2 - 12, text=self._title, anchor="w", fill="white", font=self._tf, tags="txt")
        self.create_text(24, h // 2 + 14, text=self._subtitle, anchor="w", fill=_hex(_mix(self._light, (255, 255, 255), 0.0)), font=self._sf, tags="txt")
        n = max(18, min(70, w // 38))
        self._flies = []
        for _ in range(n):
            r = random.uniform(1.4, 2.8)
            fly = dict(
                x=random.uniform(0, w), y=random.uniform(0, h), r=r,
                vx=random.uniform(-0.35, 0.35), vy=random.uniform(-0.25, 0.05),
                ph=random.uniform(0, 6.28), sp=random.uniform(0.03, 0.09),
                ids=[self.create_oval(0, 0, 0, 0, outline="") for _ in range(3)],
            )
            self._flies.append(fly)
        self.tag_raise("txt")  # o título fica por cima das luzes
        self._step(first=True)

    def _step(self, first: bool = False) -> None:
        w, h = self._cw, self._h
        for f in self._flies:
            f["ph"] += f["sp"]
            f["x"] += f["vx"] + math.sin(f["ph"] * 0.7) * 0.25
            f["y"] += f["vy"] + math.cos(f["ph"] * 0.5) * 0.15
            if f["x"] < -8:
                f["x"] = w + 8
            elif f["x"] > w + 8:
                f["x"] = -8
            if f["y"] < -8:
                f["y"] = h + 8
            elif f["y"] > h + 8:
                f["y"] = -8
            pulse = 0.55 + 0.45 * math.sin(f["ph"])
            bg = gradient_color(int(max(0, min(h - 1, f["y"]))), h, self._base, self._glow)
            x, y, r = f["x"], f["y"], f["r"]
            for ring, (mult, strength) in zip(f["ids"], ((3.6, 0.07), (2.2, 0.22), (1.0, 1.0))):
                rr = r * mult
                self.coords(ring, x - rr, y - rr, x + rr, y + rr)
                self.itemconfigure(ring, fill=_hex(_mix(bg, self._light, strength * pulse)))

    # ---- animação
    def start(self) -> None:
        if self._job is None:
            self._job = self.after(FPS_MS, self._loop)

    def stop(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _loop(self) -> None:
        self._job = None
        try:
            if self._flies and self.winfo_viewable():  # parada quando a janela está minimizada
                self._step()
            self._job = self.after(FPS_MS, self._loop)
        except tk.TclError:
            pass  # janela fechada
