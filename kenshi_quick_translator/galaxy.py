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
HUES = {"galaxia": 226, "verde": 138, "vermelho": 355, "amarelo": 46, "laranja": 24, "roxo": 272, "rosa": 328,
        "preto": 220, "branco": 220}
THEME_NAMES = {
    "galaxia": "Azul galáxia", "verde": "Verde aurora", "vermelho": "Vermelho supernova", "amarelo": "Amarelo solar",
    "laranja": "Laranja crepúsculo", "roxo": "Roxo nebulosa", "rosa": "Rosa quasar",
    "preto": "Preto eclipse", "branco": "Branco lunar",
}
LIGHT_THEMES = ("branco",)  # temas claros: faixa clara com letra escura


def _rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, s, v)
    return (round(r * 255), round(g * 255), round(b * 255))


def fx_colors(theme: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """(topo escuro, brilho de baixo, cor das luzes) do tema."""
    if theme == "preto":  # grafite: topo quase preto, brilho cinza-azulado
        return (10, 10, 13), (118, 126, 146), (232, 236, 248)
    if theme == "branco":  # perolado: topo branco, brilho lavanda; as luzes são escuras para aparecer
        return (247, 249, 253), (168, 184, 216), (96, 112, 156)
    h = HUES.get(theme, 226)
    glow_v = 1.0 if h in (46, 24, 138) else 0.95
    return _rgb(h, 0.75, 0.11), _rgb(h, 0.85 if h != 46 else 0.9, glow_v), _rgb(h, 0.32, 1.0)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


def _hex(c: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % c


def aurora(x: float, w: int) -> float:
    """Intensidade do brilho (0.62 a 1.0) ao longo da largura: duas ondas suaves dão manchas de luz, como uma aurora."""
    u = x / max(1, w)
    v = 0.81 + 0.13 * math.sin(u * 8.2 + 0.9) + 0.06 * math.sin(u * 19.0 + 2.3)
    return max(0.62, min(1.0, v))


def gradient_color(y: int, height: int, base=None, glow=None, x: float | None = None, width: int = 0) -> tuple[int, int, int]:
    """Cor do fundo na altura y: escuro no topo, brilho colorido embaixo (cresce de forma suave).
    Com x e width, o brilho varia ao longo da faixa (manchas de luz)."""
    b0, g0, _ = fx_colors("galaxia")
    t = y / max(1, height - 1)
    k = aurora(x, width) if x is not None and width else 1.0
    return _mix(base or b0, glow or g0, (t ** 2.2) * 0.97 * k)


class GalaxyBanner(tk.Canvas):
    def __init__(self, parent: tk.Misc, title: str, subtitle: str, title_font, sub_font, height: int = 86,
                 theme: str = "galaxia") -> None:
        self._base, self._glow, self._light = fx_colors(theme)
        self._tc, self._sc = ("#1f2933", "#4a5a73") if theme in LIGHT_THEMES else ("white", None)
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=_hex(self._base))
        self._h = height
        self._cw = 0
        self._img: tk.PhotoImage | None = None
        self._flies: list[dict] = []
        self._job: str | None = None
        self._paint_job: str | None = None
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
        if self._paint_job is not None:
            self.after_cancel(self._paint_job)
        self._paint_job = self.after(50 if self._flies else 0, self._paint)  # ao arrastar a borda, pinta só quando para

    def _paint(self) -> None:
        self._paint_job = None
        w, h = self._cw, self._h
        self.delete("all")
        step = 4  # a imagem é feita 4x mais estreita e ampliada: rápido e sem faixas visíveis
        cols = max(1, w // step + 1)
        small = tk.PhotoImage(width=cols, height=h)
        edge = _mix(self._glow, (0, 0, 0) if self._tc != "white" else (255, 255, 255), 0.18 if self._tc != "white" else 0.35)
        for y in range(h):
            row = [gradient_color(y, h, self._base, self._glow, x * step, w) for x in range(cols)]
            if y >= h - 2:  # fio de luz na borda de baixo separa a faixa do conteúdo
                mix = 0.55 if y == h - 1 else 0.22
                row = [_mix(c, edge, mix) for c in row]
            small.put("{" + " ".join(_hex(c) for c in row) + "}", to=(0, y))
        img = small.zoom(step, 1)
        self._img = img  # o Tk não guarda a imagem sozinho
        self.create_image(0, 0, image=img, anchor="nw")
        self.create_text(22, h // 2 - 12, text=self._title, anchor="w", fill=self._tc, font=self._tf, tags="txt")
        self.create_text(24, h // 2 + 14, text=self._subtitle, anchor="w", fill=self._sc or _hex(self._light), font=self._sf, tags="txt")
        self._flies = []
        n = max(22, min(64, w // 34))
        for i in range(n):
            # 3 camadas de profundidade: ao fundo (pequenas, lentas, fracas), do meio (brilhantes) e bolhas grandes e suaves
            kind = "bolha" if i % 7 == 0 else ("meio" if i % 7 in (2, 4, 6) else "fundo")
            r = {"bolha": random.uniform(6.0, 12.0), "meio": random.uniform(1.8, 3.0), "fundo": random.uniform(1.0, 1.7)}[kind]
            speed = {"bolha": 0.35, "meio": 0.7, "fundo": 0.5}[kind]
            if kind == "bolha":
                ids = [self.create_oval(0, 0, 0, 0, outline=""), self.create_oval(0, 0, 0, 0, fill="")]
            else:
                ids = [self.create_oval(0, 0, 0, 0, outline="") for _ in range(3)]
            self._flies.append(dict(
                kind=kind, x=random.uniform(0, w), y=random.uniform(0, h), r=r,
                vx=random.uniform(-0.12, 0.12) * speed, vy=-random.uniform(0.08, 0.3) * speed,  # sobem devagar, como bolhas
                ph=random.uniform(0, 6.28), sp=random.uniform(0.02, 0.07) * (0.6 if kind == "bolha" else 1.0), ids=ids))
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
            if f["y"] > h + 40:
                f["y"] = -8
            pulse = 0.55 + 0.45 * math.sin(f["ph"])
            margin = f["r"] * 2 + 4
            if f["y"] < -margin:  # saiu por cima: volta por baixo num ponto novo
                f["y"] = h + margin
                f["x"] = random.uniform(0, w)
            bg = gradient_color(int(max(0, min(h - 1, f["y"]))), h, self._base, self._glow, f["x"], w)
            x, y, r = f["x"], f["y"], f["r"]
            if f["kind"] == "bolha":  # disco bem suave com um aro fino de luz
                disc, rim = f["ids"]
                self.coords(disc, x - r, y - r, x + r, y + r)
                self.coords(rim, x - r, y - r, x + r, y + r)
                self.itemconfigure(disc, fill=_hex(_mix(bg, self._light, 0.07 + 0.05 * pulse)))
                self.itemconfigure(rim, outline=_hex(_mix(bg, self._light, 0.20 + 0.14 * pulse)))
                continue
            top = 1.0 if f["kind"] == "meio" else 0.55  # as do fundo são mais discretas
            for ring, (mult, strength) in zip(f["ids"], ((4.0, 0.06), (2.4, 0.2), (1.0, 1.0))):
                rr = r * mult
                self.coords(ring, x - rr, y - rr, x + rr, y + rr)
                self.itemconfigure(ring, fill=_hex(_mix(bg, self._light, strength * top * (0.4 + 0.6 * pulse))))

    # ---- animação
    def start(self) -> None:
        if self._job is None:
            self._job = self.after(FPS_MS, self._loop)

    def stop(self) -> None:
        if self._paint_job is not None:
            try:
                self.after_cancel(self._paint_job)
            except tk.TclError:
                pass
            self._paint_job = None
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
