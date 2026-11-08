"""
Janela do programa (Tkinter, que já vem com o Python no Windows).

Só desenha e repassa para `Session`, onde fica a lógica testada. Tudo o que
demora (ler mod grande, detectar idiomas, traduzir) roda em outra thread e
avisa a janela por uma fila, então a janela nunca trava.

Organização da tela:
  esquerda: seus mods (idioma e progresso de cada um)
  direita : 1 Mod escolhido -> 2 Como traduzir -> 3 Revise e gere
"""

from __future__ import annotations

import dataclasses
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import __version__, i18n, tutorial
from .errorreport import format_exc, log_error
from .config import Config
from .core import ProviderBroken
from .glossary import Glossary, list_presets, load_preset, presets_for
from .langdetect import lang_name
from .locate import ModEntry
from .providers import LANGUAGES, SPECS, ProviderError, friendly_error
from .ui_actions import ActionsMixin, install_notice
from .ui_tools import ToolsMixin
from .ui_tips import TIP_FREE_DOWN, TIP_FREE_UP, TIP_LIST_DOWN, TIP_LIST_UP, TIP_MULTI_LANG, find_tip
from .ui_extra import TIPS_BY_TEXT, RateTracker, icon_factor, pick_icon_file, sparkline_coords
from .freeproviders import DEFAULT_ORDER, FREE_CLASSES
from .services import KINDS, PRESETS, build_aggregate, build_service
from .session import Session, ManyResult, language_label, present_languages
from .ui_state import FONT_STEPS, NARROW_WIDTH, clamp_geometry, clamp_scale, step_font

# ------------------------------------------------------------------ cores
PALETTES: dict[str, dict[str, str]] = {
    "light": dict(
        BG="#f4f5f8", CARD="#ffffff", INK="#1f2933", MUTED="#6b7785", LINE="#dfe3ea", HEAD="#1d2b3a",
        ACCENT="#2b6fe0", GREEN="#2e9d57", GREEN_DK="#237a43", RED="#c93c3c",
        BTN="#e7eaf0", BTN_ACT="#d7dce6", BTN_OFF="#eef0f4", HEADING="#eceff4", TROUGH="#e3e7ee",
        DONE="#e3f5ea", PART="#fff6d6", ATT="#fff3cd", REV="#d9f2df", IGN="#8a94a1", SRC="#f2f4f7",
        WARN="#8f5f00", OKFG="#1b7a34", HEADSUB="#a9b6c6",
        GREEN_OFF="#a9d4b9", GREEN_OFF_FG="#f0f7f2", ACC_ACT="#1f55b3", ACC_OFF="#a9c1ee", ACC_OFF_FG="#f0f4fc",
        RED_ACT="#a82f2f", RED_OFF="#e6b4b4", RED_OFF_FG="#fbf1f1",
    ),
    "dark": dict(
        BG="#14181f", CARD="#1c222b", INK="#e6e9ee", MUTED="#9aa5b3", LINE="#2c3440", HEAD="#0e1217",
        ACCENT="#3672d6", GREEN="#2e9d57", GREEN_DK="#237a43", RED="#c24a4a",
        BTN="#2a313c", BTN_ACT="#364050", BTN_OFF="#222831", HEADING="#242b35", TROUGH="#2f3743",
        DONE="#1f3a2a", PART="#3d3517", ATT="#46391a", REV="#264d36", IGN="#6f7a88", SRC="#232a34",
        WARN="#e0b04a", OKFG="#5cc47c", HEADSUB="#8b99ab",
        GREEN_OFF="#2b5a3d", GREEN_OFF_FG="#8fa89a", ACC_ACT="#2f68c4", ACC_OFF="#2c4670", ACC_OFF_FG="#8d9bb5",
        RED_ACT="#b03e3e", RED_OFF="#5a3030", RED_OFF_FG="#b59a9a",
    ),
    "galaxia": dict(
        BG="#0a0f24", CARD="#111a38", INK="#e8ecff", MUTED="#8f9bc7", LINE="#233060", HEAD="#070b1c",
        ACCENT="#4a7dff", GREEN="#2e9d6f", GREEN_DK="#237a57", RED="#c24a62",
        BTN="#1b2650", BTN_ACT="#26356b", BTN_OFF="#151e42", HEADING="#17214a", TROUGH="#1f2a58",
        DONE="#183a3a", PART="#3a3416", ATT="#46391a", REV="#1d4d46", IGN="#6c78a8", SRC="#141d40",
        WARN="#e0b04a", OKFG="#5fd0a0", HEADSUB="#9fb4ff",
        GREEN_OFF="#25506a", GREEN_OFF_FG="#9ab8c8", ACC_ACT="#3a67e0", ACC_OFF="#2a3d78", ACC_OFF_FG="#93a3d6",
        RED_ACT="#b04060", RED_OFF="#522a40", RED_OFF_FG="#c19aa8",
    ),
}


def _hue_palette(hue: float) -> dict[str, str]:
    """Paleta escura de um tema colorido: as cores "de superfície" giram do azul da galáxia para o matiz
    pedido; as de significado (verde = feito, vermelho = parar, aviso) ficam como estão."""
    import colorsys

    base = PALETTES["galaxia"]
    shift = (hue - 226) / 360.0
    spin = ("BG", "CARD", "INK", "MUTED", "LINE", "HEAD", "BTN", "BTN_ACT", "BTN_OFF", "HEADING", "TROUGH",
            "SRC", "IGN", "HEADSUB", "ACC_OFF_FG")
    out = dict(base)

    def rot(c: str, s_mul: float = 1.0, v_mul: float = 1.0) -> str:
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
        h, sat, val = colorsys.rgb_to_hsv(r, g, b)
        r, g, b = colorsys.hsv_to_rgb((h + shift) % 1.0, min(1.0, sat * s_mul), min(1.0, val * v_mul))
        return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))

    # matizes quentes e o verde ficavam turvos (marrom/oliva) com a saturação do azul: menos saturação neles
    sat = 0.52 if 30 < hue < 70 else 0.66 if 10 <= hue <= 30 else 0.82 if 100 < hue < 180 else 0.9 if hue > 300 or hue < 10 else 1.0
    for k in spin:
        out[k] = rot(base[k], s_mul=sat)
    val = 0.66 if 30 < hue < 70 else (0.74 if hue < 40 or 120 < hue < 170 else 0.82)  # amarelo/laranja/verde mais escuros: texto branco legível
    r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 0.72, val)
    out["ACCENT"] = "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))
    acc = [int(out["ACCENT"][i:i + 2], 16) for i in (1, 3, 5)]
    card = [int(out["CARD"][i:i + 2], 16) for i in (1, 3, 5)]
    out["ACC_ACT"] = "#%02x%02x%02x" % tuple(round(c * 0.84) for c in acc)
    out["ACC_OFF"] = "#%02x%02x%02x" % tuple(round(card[i] * 0.6 + acc[i] * 0.4) for i in range(3))
    return out


def _lum(c: str) -> float:
    def f(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _with_white_text(color: str, need: float = 4.6) -> str:
    """Escurece a cor até o texto branco por cima dela ter contraste suficiente (WCAG)."""
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    for _ in range(40):
        if 1.05 / (_lum("#%02x%02x%02x" % tuple(c)) + 0.05) >= need:
            break
        c = [round(v * 0.96) for v in c]
    return "#%02x%02x%02x" % tuple(c)


PALETTES["preto"] = dict(
    PALETTES["dark"], BG="#0c0c0f", CARD="#151519", INK="#ececf2", MUTED="#9a9aa6", LINE="#2a2a31", HEAD="#08080a",
    ACCENT="#5a6a90", BTN="#232329", BTN_ACT="#32323a", BTN_OFF="#1b1b20", HEADING="#1d1d23", TROUGH="#2c2c34",
    SRC="#1a1a1f", IGN="#74747f", HEADSUB="#aab0c4", ACC_ACT="#4c5b80", ACC_OFF="#2e3345", ACC_OFF_FG="#9a9fb0",
)
PALETTES["branco"] = dict(PALETTES["light"], BG="#f5f6fa", HEAD="#f7f9fd", HEADSUB="#4a5a73")
for _name, _hue in (("verde", 138), ("vermelho", 355), ("amarelo", 46), ("laranja", 24), ("roxo", 272), ("rosa", 328)):
    PALETTES[_name] = _hue_palette(_hue)
for _pal in PALETTES.values():  # botões de destaque (texto branco) legíveis em todos os temas
    _pal["ACCENT"] = _with_white_text(_pal["ACCENT"])
    _pal["ACC_ACT"] = _with_white_text("#%02x%02x%02x" % tuple(round(int(_pal["ACCENT"][i:i + 2], 16) * 0.86) for i in (1, 3, 5)))
EFFECT_THEMES = ("galaxia", "verde", "vermelho", "amarelo", "laranja", "roxo", "rosa", "preto", "branco")
THEME = "light"
BG = CARD = INK = MUTED = LINE = HEAD = ACCENT = GREEN = GREEN_DK = RED = ""
BTN = BTN_ACT = BTN_OFF = HEADING = TROUGH = DONE = PART = ATT = REV = IGN = SRC = WARN = OKFG = HEADSUB = ""
GREEN_OFF = GREEN_OFF_FG = ACC_ACT = ACC_OFF = ACC_OFF_FG = RED_ACT = RED_OFF = RED_OFF_FG = ""


def system_theme() -> str:
    """'dark' se o Windows está no modo escuro para aplicativos; senão 'light'."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return "light" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "dark"
    except Exception:  # noqa: BLE001 - fora do Windows ou sem a chave: claro
        return "light"


def set_palette(choice: str) -> dict[str, str]:
    """Troca as cores do módulo. choice: 'light', 'dark' ou 'auto'. Devolve a paleta ANTERIOR."""
    global THEME
    old = dict(PALETTES[THEME]) if BG else dict(PALETTES["light"])
    THEME = system_theme() if choice == "auto" else (choice if choice in PALETTES else "light")
    globals().update(PALETTES[THEME])
    return old


set_palette("light")

MAX_ROWS = 1500  # linhas desenhadas na tabela; mods enormes têm filtro e busca para o resto
MULTI_CHOICES = ["en", "zh", "ja", "ko", "ru", "uk", "es", "fr", "de", "pt", "it", "pl", "tr"]

STATUS_LABEL = {
    "pendente": "Pendente",
    "automatica": "Automática",
    "revisada": "Revisada",
    "atencao": "Conferir",
    "ignorada": "Ignorada",
}
FILTER_LABEL = {
    "todos": "Todos",
    "pendente": "Pendentes",
    "atencao": "Para conferir",
    "duvidosa": "Duvidosos",
    "automatica": "Automáticas",
    "revisada": "Revisadas",
    "ignorada": "Ignoradas",
}
SOURCE_LABEL = {"local": "Pasta mods", "workshop": "Workshop", "avulso": "Arquivo"}
FIELD_NOTES_TITLE = "Campos deixados em inglês por parecerem código do jogo (para traduzir algum, escreva o nome dele em translator_liberados.txt):"

MODFILTER_LABEL = {
    "todos": "Todos",
    "sem": "Sem tradução",
    "incompleto": "Incompletos",
    "completo": "Completos",
    "workshop": "Só Workshop",
    "local": "Só pasta do jogo",
}
MODSORT_LABEL = {
    "padrao": "Padrão",
    "nome": "Nome (A–Z)",
    "menos": "Menos traduzidos primeiro",
    "mais": "Mais traduzidos primeiro",
    "tamanho": "Maiores primeiro",
}
MODE_LABELS = {
    "completo": "Completo: mesmo nome do original, ocupa o lugar dele (não depende do original)",
    "dependente": "Dependente: arquivo pequeno “Nome IDIOMA”, precisa do original",
}
MODE_NOTE = ("Completo: o mod traduzido é uma cópia do original com os textos traduzidos, tem o mesmo nome e o substitui no jogo "
             "(o original fica guardado como backup). Dependente: só o que mudou, num arquivo com o idioma no nome "
             "(ex.: “Nome PT-BR”), e o original precisa continuar instalado.")
CREDITS_TEXT = ("Inspirado no Kenshi Translator, de Kakrain. Feito por Canela de Enxadeco, "
                "com a ajuda de uma IA (Claude, da Anthropic).")
CREDITS_URL = "https://github.com/Kakrain"
FONT_NAMES = {85: "Letra pequena", 100: "Letra normal", 115: "Letra grande", 130: "Letra muito grande", 150: "Letra enorme"}
SHORTCUTS = (
    ("Ctrl+T", "traduzir este mod"),
    ("Ctrl+Shift+T", "traduzir os mods selecionados"),
    ("Esc", "parar (ou fechar a lista de mods)"),
    ("F5", "atualizar a lista de mods"),
    ("F6", "gerar o mod de tradução"),
    ("F7", "instalar no jogo"),
    ("Ctrl+Enter", "aplicar a edição e ir ao próximo"),
    ("Ctrl+Shift+Z", "desfazer a última edição de texto"),
    ("Ctrl+F", "buscar nos textos"),
    ("Ctrl+Shift+F", "buscar na lista de mods"),
    ("F9", "abrir/fechar a lista de mods (janela estreita)"),
    ("Ctrl + / Ctrl −", "aumentar / diminuir a letra"),
    ("Ctrl+0", "letra no tamanho normal"),
)
LIGHT_OK, LIGHT_WAIT, LIGHT_BAD = "#2e9e5b", "#d9a400", "#d14343"


class Tip:
    """Dica que aparece ao passar o mouse sobre um widget (texto vem de uma função, para ficar sempre atual)."""

    def __init__(self, widget, text_fn) -> None:
        self.widget, self.text_fn, self.win, self._job = widget, text_fn, None, None
        widget._qt_tip = True  # a dica automática (AutoTips) não repete em quem já tem a sua
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _e=None) -> None:
        """A dica só aparece quando o mouse fica parado em cima por um instante."""
        self._hide()
        try:
            self._job = self.widget.after(500, self._show)
        except tk.TclError:
            self._job = None

    def _show(self, _e=None) -> None:
        self._job = None
        text = self.text_fn()
        if not text:
            return
        self.win = tk.Toplevel(self.widget)
        self.win.wm_overrideredirect(True)
        x, y = self.widget.winfo_rootx() + 12, self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.win.wm_geometry(f"+{x}+{y}")
        tk.Label(self.win, text=text, bg="#fffbe6", fg="#222222", relief="solid", borderwidth=1,
                 justify="left", wraplength=360, padx=6, pady=3).pack()

    def _hide(self, _e=None) -> None:
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None

class AutoTips:
    """
    Dica ao passar o mouse em TODO botão, caixa de marcar e opção do programa, inclusive nas janelas abertas depois.
    O texto vem de `text_fn(widget)`; widgets que já têm uma `Tip` própria (`_qt_tip`) são deixados em paz.
    """

    def __init__(self, root, text_fn) -> None:
        self.root, self.text_fn = root, text_fn
        self.win, self.job, self.widget = None, None, None
        for cls in ("TButton", "TCheckbutton", "TRadiobutton"):
            root.bind_class(cls, "<Enter>", self._enter, add="+")
            root.bind_class(cls, "<Leave>", self._hide, add="+")
            root.bind_class(cls, "<ButtonPress>", self._hide, add="+")
            root.bind_class(cls, "<Destroy>", self._hide, add="+")

    def _enter(self, event) -> None:
        w = event.widget
        self._hide()
        if getattr(w, "_qt_tip", False):
            return
        try:
            text = self.text_fn(w)
        except Exception:  # noqa: BLE001 - dica nunca pode derrubar a janela
            return
        if not text:
            return
        self.widget = w
        self.job = self.root.after(500, lambda: self._show(w, text))  # só aparece se o mouse ficar parado

    def _show(self, w, text: str) -> None:
        self.job = None
        try:
            if not w.winfo_exists():
                return
            self.win = tk.Toplevel(w)
            self.win.wm_overrideredirect(True)
            x, y = w.winfo_rootx() + 12, w.winfo_rooty() + w.winfo_height() + 4
            self.win.wm_geometry(f"+{x}+{y}")
            tk.Label(self.win, text=text, bg="#fffbe6", fg="#222222", relief="solid", borderwidth=1,
                     justify="left", wraplength=360, padx=6, pady=3).pack()
        except tk.TclError:
            self.win = None

    def _hide(self, event=None) -> None:
        if event is not None and event.type == tk.EventType.Destroy and event.widget is not self.widget:
            return  # outro widget foi destruído: a dica atual continua
        if self.job is not None:
            try:
                self.root.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
        if event is None or event.type != tk.EventType.Enter:
            self.widget = None


class Tour:
    """Tutorial guiado (básico ou avançado): destaca uma parte da janela de cada vez e explica o que fazer nela."""

    RING = 3  # espessura da moldura em volta da parte destacada

    def __init__(self, app: "App", kind: str = "basic") -> None:
        self.app, self.kind, self.i = app, kind, 0
        self.steps = [s for s in tutorial.steps_for(kind) if app._tut_target(s[0]) is not None]
        self.saved: tuple | None = None
        self.ring: list[tk.Frame] = []
        self._ring_geo: tuple | None = None
        self._job: str | None = None
        self.closed = False
        root = app.root
        self.win = tk.Toplevel(root)
        self.win._tip_ctx = "tour"
        self.win.title(i18n.tr("Tutorial avançado" if kind == "advanced" else "Tutorial básico"))
        self.win.transient(root)
        self.win.resizable(False, False)
        self.win.configure(bg=CARD)
        body = tk.Frame(self.win, bg=CARD, padx=18, pady=14)
        body.pack(fill="both", expand=True)
        self.count = tk.Label(body, bg=CARD, fg=MUTED, font=app.f_small, anchor="w")
        self.count.pack(fill="x")
        self.title = tk.Label(body, bg=CARD, fg=INK, font=app.f_big, anchor="w", justify="left")
        self.title.pack(fill="x", pady=(2, 6))
        self.text = tk.Label(body, bg=CARD, fg=INK, font=app.f_base, anchor="w", justify="left",
                             wraplength=max(380, round(460 * app.scale)))
        self.text.pack(fill="x")
        bar = tk.Frame(body, bg=CARD)
        bar.pack(fill="x", pady=(14, 0))
        self.b_skip = ttk.Button(bar, text="Pular", command=self.close)
        self.b_skip.pack(side="left")
        self.b_adv = ttk.Button(bar, text="Ver o tutorial avançado", command=self.go_advanced)
        self.b_next = ttk.Button(bar, text="Próximo", style="Accent.TButton", command=self.next)
        self.b_next.pack(side="right")
        self.b_back = ttk.Button(bar, text="Voltar", command=self.back)
        self.b_back.pack(side="right", padx=6)
        i18n.apply(self.win)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.bind("<Return>", lambda e: self.next())
        self.win.bind("<Right>", lambda e: self.next())
        self.win.bind("<Left>", lambda e: self.back())
        self.show()
        self._poll()

    def _target(self, key: str):
        return self.app._tut_target(key)

    # ---------------------------------------------------------------- destaque
    def _unhighlight(self) -> None:
        if self.saved is not None:
            w, color, thick = self.saved
            try:
                w.configure(highlightbackground=color, highlightthickness=thick)
            except tk.TclError:
                pass
            self.saved = None
        self._clear_ring()

    def _clear_ring(self) -> None:
        for f in self.ring:
            try:
                f.destroy()
            except tk.TclError:
                pass
        self.ring = []
        self._ring_geo = None

    def _visible_rect(self, target) -> tuple[int, int, int, int] | None:
        """Retângulo do widget em coordenadas da janela principal, recortado pela área rolável. None = não aparece."""
        root, a = self.app.root, self.app
        x0 = target.winfo_rootx() - root.winfo_rootx()
        y0 = target.winfo_rooty() - root.winfo_rooty()
        x1, y1 = x0 + target.winfo_width(), y0 + target.winfo_height()
        if x1 - x0 < 6 or y1 - y0 < 6:
            return None
        if a.scroller._inside(target):
            c = a.scroller.canvas
            cx0, cy0 = c.winfo_rootx() - root.winfo_rootx(), c.winfo_rooty() - root.winfo_rooty()
            x0, y0 = max(x0, cx0), max(y0, cy0)
            x1, y1 = min(x1, cx0 + c.winfo_width()), min(y1, cy0 + c.winfo_height())
        if x1 - x0 < 6 or y1 - y0 < 6:
            return None
        return x0, y0, x1, y1

    def _draw_ring(self, target) -> None:
        """Moldura de 4 faixas por cima do widget (os widgets ttk não têm borda de destaque própria)."""
        try:
            rect = self._visible_rect(target)
        except tk.TclError:
            rect = None
        if rect == self._ring_geo and self.ring:
            return
        self._clear_ring()
        if rect is None:
            return
        self._ring_geo = rect
        x0, y0, x1, y1 = rect
        t, root = self.RING, self.app.root
        pieces = ((x0 - t, y0 - t, x1 - x0 + 2 * t, t), (x0 - t, y1, x1 - x0 + 2 * t, t),
                  (x0 - t, y0, t, y1 - y0), (x1, y0, t, y1 - y0))
        for x, y, w, h in pieces:
            f = tk.Frame(root, bg=ACCENT)
            f.place(x=x, y=y, width=w, height=h)
            f.lift()
            self.ring.append(f)

    def _poll(self) -> None:
        """Acompanha rolagem e mudança de tamanho da janela: a moldura segue a parte destacada."""
        if self.closed:
            return
        try:
            if self.steps and self.saved is None:
                target = self._target(self.steps[self.i][0])
                if target is not None and not isinstance(target, tk.Frame):
                    self._draw_ring(target)
            self._job = self.win.after(300, self._poll)
        except tk.TclError:
            pass

    # ---------------------------------------------------------------- passos
    def show(self) -> None:
        self._unhighlight()
        if not self.steps:
            self.close()
            return
        key, title, text = self.steps[self.i]
        n = len(self.steps)
        last = self.i == n - 1
        self.count.configure(text=i18n.tr(f"Passo {self.i + 1} de {n}"))
        self.title.configure(text=i18n.tr(title))
        self.text.configure(text=i18n.tr(text))
        self.b_back.configure(state="normal" if self.i else "disabled")
        self.b_next.configure(text=i18n.tr("Concluir" if last else "Próximo"))
        if last and self.kind == "basic":
            self.b_adv.configure(text=i18n.tr("Ver o tutorial avançado"))
            self.b_adv.pack(side="left", padx=6)
        else:
            self.b_adv.pack_forget()
        target = self._target(key)
        if isinstance(target, tk.Frame):  # os cartões têm borda: ela vira o destaque
            self.saved = (target, str(target.cget("highlightbackground")), int(float(target.cget("highlightthickness"))))
            target.configure(highlightbackground=ACCENT, highlightthickness=4)
        if target is not None:
            try:
                self.app.expand_advanced_for(target)  # parte dentro das opções avançadas: abre o quadro
            except tk.TclError:
                pass
        self._scroll_to(target)
        self.win.update_idletasks()
        if target is not None and not isinstance(target, tk.Frame):
            self._draw_ring(target)
        self._place(target)

    def _scroll_to(self, target) -> None:
        a = self.app
        try:
            if target is not None and a.scroller._bar_on and a.scroller._inside(target):
                total = max(1, a.scroller.inner.winfo_height())
                y = target.winfo_rooty() - a.scroller.inner.winfo_rooty()
                a.scroller.canvas.yview_moveto(max(0.0, (y - 12) / total))
                a.root.update_idletasks()
        except tk.TclError:
            pass

    def _place(self, target) -> None:
        """Põe a janelinha onde não cobre a parte destacada (tenta embaixo/em cima e à direita/esquerda)."""
        root = self.app.root
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        rx, ry, rw, rh = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
        if target is None:
            x, y = rx + (rw - w) // 2, ry + (rh - h) // 2
        else:
            tx, ty = target.winfo_rootx(), target.winfo_rooty()
            tw, th = target.winfo_width(), target.winfo_height()
            cands = []
            for cx in (rx + rw - w - 24, rx + (rw - w) // 2, rx + 24):
                for cy in (ry + ry_off(rh, h, True), ry + ry_off(rh, h, False)):
                    cands.append((cx, cy))
            x, y = cands[0]
            for cx, cy in cands:
                cx, cy = max(0, min(cx, sw - w - 10)), max(0, min(cy, sh - h - 50))
                if cx + w <= tx or cx >= tx + tw or cy + h <= ty or cy >= ty + th:  # não cobre o alvo
                    x, y = cx, cy
                    break
        x = max(0, min(x, sw - w - 10))
        y = max(0, min(y, sh - h - 50))
        self.win.geometry(f"+{x}+{y}")

    def next(self) -> None:
        if self.i >= len(self.steps) - 1:
            self.close()
        else:
            self.i += 1
            self.show()

    def back(self) -> None:
        if self.i:
            self.i -= 1
            self.show()

    def go_advanced(self) -> None:
        app = self.app
        self.close()
        app.start_tutorial("advanced")

    def close(self) -> None:
        self.closed = True
        self._unhighlight()
        if self._job is not None:
            try:
                self.win.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        if self.app.tour is self:
            self.app.tour = None


def ry_off(root_h: int, win_h: int, bottom: bool) -> int:
    """Deslocamento vertical da janelinha dentro da janela principal: embaixo (True) ou em cima (False)."""
    return max(0, root_h - win_h - 40) if bottom else 70


class Welcome:
    """Janela de boas-vindas: escolher o tutorial básico, o avançado ou nenhum."""

    def __init__(self, app: "App", first_run: bool) -> None:
        self.app, self.first_run = app, first_run
        root = app.root
        self.win = tk.Toplevel(root)
        self.win._tip_ctx = "welcome"
        self.win.title(i18n.tr("Tutoriais"))
        self.win.transient(root)
        self.win.resizable(False, False)
        self.win.configure(bg=CARD)
        wrap = max(380, round(420 * app.scale))
        body = tk.Frame(self.win, bg=CARD, padx=26, pady=20)
        body.pack(fill="both", expand=True)
        head = "Bem-vindo ao Kenshi Quick Translator!" if first_run else "Tutoriais"
        tk.Label(body, text=i18n.tr(head), bg=CARD, fg=INK, font=app.f_title, anchor="w", justify="left",
                 wraplength=wrap).pack(fill="x")
        tk.Label(body, text=i18n.tr("Traduza mods do Kenshi sem estragar os marcadores do jogo. Como você quer começar?"),
                 bg=CARD, fg=MUTED, font=app.f_base, anchor="w", justify="left", wraplength=wrap).pack(fill="x", pady=(4, 14))
        for kind, label, desc, style in (
            ("basic", "Tutorial básico",
             "Só o essencial: escolher o mod, traduzir, conferir e instalar. Leva cerca de 2 minutos.", "Primary.TButton"),
            ("advanced", "Tutorial avançado",
             "Explica cada parte da tela e cada botão, um por um, na ordem em que aparecem.", "Accent.TButton"),
        ):
            ttk.Button(body, text=i18n.tr(label), style=style, command=lambda k=kind: self.choose(k)).pack(fill="x")
            tk.Label(body, text=i18n.tr(desc), bg=CARD, fg=MUTED, font=app.f_small, anchor="w", justify="left",
                     wraplength=wrap).pack(fill="x", pady=(3, 12))
        self.dont = tk.BooleanVar(value=True)
        if first_run:
            ttk.Checkbutton(body, text=i18n.tr("Não mostrar isto ao abrir o programa"), variable=self.dont,
                            style="Card.TCheckbutton").pack(anchor="w", pady=(2, 0))
        tk.Label(body, text=i18n.tr("Você pode abrir os tutoriais quando quiser, no botão “Tutorial” no topo da janela."),
                 bg=CARD, fg=MUTED, font=app.f_small, anchor="w", justify="left", wraplength=wrap).pack(fill="x", pady=(6, 10))
        ttk.Button(body, text=i18n.tr("Agora não, vou explorar sozinho"), command=self.close).pack(anchor="e")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.bind("<Return>", lambda e: self.choose("basic"))
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        x = root.winfo_rootx() + (root.winfo_width() - w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - h) // 3
        self.win.geometry(f"+{max(0, min(x, sw - w - 10))}+{max(0, min(y, sh - h - 50))}")
        try:
            self.win.lift()
            self.win.focus_force()
        except tk.TclError:
            pass

    def _finish(self) -> None:
        if self.first_run and self.dont.get():
            self.app.cfg.tour_done = True
            try:
                self.app.cfg.save()
            except OSError:
                pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        if self.app.welcome is self:
            self.app.welcome = None

    def choose(self, kind: str) -> None:
        app = self.app
        self._finish()
        app.start_tutorial(kind)

    def close(self) -> None:
        self._finish()


HELP_TEXT = (
    "Como usar, em 3 passos:\n\n"
    "1. Clique num mod na lista da esquerda (ou em “Abrir arquivo…”).\n"
    "    Ctrl+clique escolhe vários mods para traduzir em fila.\n\n"
    "2. Escolha o idioma de destino e o serviço de tradução e clique em “Traduzir”.\n"
    "    Se o mod tem mais de um idioma (por exemplo inglês e chinês), marque a opção\n"
    "    “Este mod tem mais de um idioma”. O programa já sugere isso sozinho.\n\n"
    "3. Confira as linhas amarelas (“Conferir”), corrija o que quiser na caixa da direita\n"
    "    e clique em “Gerar mod de tradução” ou “Instalar no jogo”.\n\n"
    "O arquivo do mod original não é alterado ao gerar; ao instalar, o original fica guardado como backup. O trabalho fica salvo: pode fechar e continuar depois."
)


def lang_display(code: str) -> str:
    return f"{LANGUAGES[code]} ({code})" if code != "auto" else LANGUAGES["auto"]


def one_line(text: str, limit: int = 90) -> str:
    flat = text.replace("\r", "").replace("\n", " ⏎ ")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def open_with_system(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ScrollFrame(ttk.Frame):
    """
    Área com barra de rolagem que só aparece quando o conteúdo não cabe.

    Se a janela for grande, o conteúdo estica para ocupar o espaço; se for
    pequena (notebook), tudo continua alcançável rolando, em vez de os botões
    de baixo ficarem cortados.
    """

    def __init__(self, parent, bg: str) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, bg=bg)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        self._bar_on = False
        self._last_req = -1
        self.inner.bind("<Configure>", lambda e: self._fit())
        self.canvas.bind("<Configure>", lambda e: self._fit())
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._wheel, add="+")
        self.after(200, self._tick)

    def _tick(self) -> None:
        """
        Reavalia quando o CONTEÚDO muda de altura (ex.: ao ligar a opção de vários
        idiomas). Como a altura da área é fixada pela própria rolagem, o Tk não
        avisa sozinho quando o conteúdo passa a pedir mais espaço.
        """
        try:
            if self.inner.winfo_reqheight() != self._last_req:
                self._fit()
            self.after(250, self._tick)
        except tk.TclError:
            pass  # janela fechada

    def _fit(self) -> None:
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        need = self.inner.winfo_reqheight()
        self._last_req = need
        total = max(h, need)
        self.canvas.itemconfigure(self._win, width=w, height=total)
        self.canvas.configure(scrollregion=(0, 0, w, total))
        want_bar = need > h + 1
        if want_bar != self._bar_on:
            self._bar_on = want_bar
            if want_bar:
                self.vsb.pack(side="right", fill="y")
            else:
                self.vsb.pack_forget()
                self.canvas.yview_moveto(0)

    def _inside(self, widget) -> bool:
        while widget is not None:
            if widget is self.inner:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _wheel(self, event) -> None:
        if not self._bar_on:
            return
        under = self.winfo_containing(event.x_root, event.y_root)
        if under is None or not self._inside(under):
            return
        if under.winfo_class() in ("Treeview", "Text", "Listbox", "TCombobox"):
            return  # esses rolam sozinhos
        step = -1 if (getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0) else 1
        self.canvas.yview_scroll(step * 2, "units")


class App(ActionsMixin, ToolsMixin):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.session = Session()
        self.cfg = self.session.cfg
        self.events: queue.Queue[tuple] = queue.Queue()
        self.cancel = threading.Event()
        self.worker: threading.Thread | None = None
        self.last_built: Path | None = None
        self.last_refresh = 0.0
        self.selected: int | None = None
        self.entries: list[ModEntry] = []
        self.mod_gen = 0  # troca a cada atualização da lista, para descartar respostas antigas
        self.counts: dict[str, int] = {}
        self._t0: float | None = None
        self._d0 = 0
        self._sel_after: str | None = None
        self._query_after: str | None = None
        self._stoppable = False
        self._narrow = False  # janela estreita: a lista de mods vira gaveta
        self._drawer_open = False
        self._wrap_after: str | None = None
        self._sel_restored = False
        self.rate = RateTracker()  # velocidade ao longo da tradução (gráfico)
        self._icons: dict[Path, object] = {}  # imagem pequena de cada mod (None = sem imagem)
        self._icon_todo: list[tuple[Path, str]] = []
        self._icon_iids: dict[Path, str] = {}
        self._icon_after: str | None = None
        self.cards: dict[str, tk.Frame] = {}
        self.tt: dict[str, object] = {}  # partes da janela que o tutorial destaca (ver _tut_target)
        self.tour: Tour | None = None
        self.welcome: Welcome | None = None

        root.title(f"Kenshi Quick Translator {__version__}")
        self._install_error_hook()
        self._restore_window()
        set_palette(self.cfg.theme)
        root.configure(bg=BG)  # depois da paleta: senão a janela abre com o fundo do tema claro
        i18n.set_language(self.cfg.ui_lang)
        i18n.install_hooks()
        self._fonts()
        self._style()
        self._build_header()
        self._build_body()
        self._fill_from_config()
        self._attach_tips()  # antes do i18n.apply: ainda lê os textos originais em português
        self.auto_tips = AutoTips(root, self._auto_tip_text)  # todo botão sem dica própria, em qualquer janela
        self.refresh_mods()
        i18n.apply(root)
        self._recolor(root, {})  # widgets de cor padrão (caixas de texto) também seguem o tema
        self._sync_galaxy()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<Control-Return>", lambda e: self.apply_edit())
        root.bind("<Configure>", self._on_root_configure, add="+")
        self._bind_shortcuts()
        root.after(100, self._poll)
        if not self.cfg.tour_done:
            root.after(1200, lambda: self.open_tutorial_menu(first_run=True))

    # ================================================================ estilo
    def _fonts(self) -> None:
        """Cria as fontes na primeira vez; depois só muda o tamanho (as telas já abertas acompanham sozinhas)."""
        if not hasattr(self, "f_bold"):
            base = tkfont.nametofont("TkDefaultFont")
            self.f_base = base
            self.f_bold, self.f_title, self.f_small, self.f_big = (base.copy() for _ in range(4))
            self.f_bold.configure(weight="bold")
            self.f_title.configure(weight="bold")
            self.f_big.configure(weight="bold")
        self.scale = clamp_scale(self.cfg.font_scale) / 100

        def sz(n: int) -> int:
            return max(7, round(n * self.scale))

        self.f_base.configure(size=sz(10))
        self.f_bold.configure(size=sz(10))
        self.f_title.configure(size=sz(15))
        self.f_small.configure(size=sz(9))
        self.f_big.configure(size=sz(11))
        tkfont.nametofont("TkTextFont").configure(size=sz(11))

    def set_font_scale(self, pct: int) -> None:
        pct = clamp_scale(pct)
        if pct == clamp_scale(self.cfg.font_scale):
            return
        self.cfg.font_scale = pct
        self.cfg.save()
        self._fonts()
        self._style()  # a altura das linhas das tabelas também acompanha
        self._style_tags()
        self._icons.clear()  # o tamanho do ícone acompanha a letra
        self._icon_todo.clear()
        self.fill_mod_tree()
        self.root.update_idletasks()
        self.status_var.set(i18n.tr(FONT_NAMES.get(pct, "Letra")) + f" ({pct}%)")

    def zoom(self, direction: int) -> None:
        self.set_font_scale(step_font(self.cfg.font_scale, direction))

    def _style(self) -> None:
        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=INK, font=self.f_base, bordercolor=LINE, lightcolor=BG, darkcolor=BG)
        st.configure("Card.TFrame", background=CARD)
        st.configure("Card.TLabel", background=CARD, foreground=INK)
        st.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=self.f_small)
        st.configure("Bold.TLabel", background=CARD, foreground=INK, font=self.f_bold)
        st.configure("Card.TCheckbutton", background=CARD, foreground=INK, focuscolor=CARD)
        st.configure("Card.TCheckbutton", indicatorbackground=BTN, indicatorforeground=INK)
        st.map("Card.TCheckbutton", background=[("active", CARD)],
               indicatorbackground=[("selected", GREEN), ("active", BTN_ACT), ("!selected", BTN)],
               indicatorforeground=[("selected", "white")])
        st.configure("TButton", padding=(10, 5), background=BTN, foreground=INK, borderwidth=1, bordercolor=LINE,
                     lightcolor=BTN, darkcolor=BTN, focuscolor=BTN)
        self.root.option_add("*TButton.cursor", "hand2")  # mãozinha nos botões
        self.root.option_add("*TCheckbutton.cursor", "hand2")
        st.map("TButton", background=[("active", BTN_ACT), ("disabled", BTN_OFF)], foreground=[("disabled", MUTED)])
        st.configure("TMenubutton", padding=(10 + round(18 * self.scale), 5, 10, 5), anchor="center", background=BTN, foreground=INK, borderwidth=1, bordercolor=LINE,
                     lightcolor=BTN, darkcolor=BTN, arrowcolor=INK)
        st.map("TMenubutton", background=[("active", BTN_ACT), ("disabled", BTN_OFF)], foreground=[("disabled", MUTED)])
        self.root.option_add("*TMenubutton.cursor", "hand2")
        st.configure("Primary.TButton", padding=(16, 9), background=GREEN, foreground="white", font=self.f_big,
                     bordercolor=GREEN, lightcolor=GREEN, darkcolor=GREEN, focuscolor=GREEN)
        st.map("Primary.TButton", bordercolor=[("disabled", GREEN_OFF)], lightcolor=[("disabled", GREEN_OFF)], darkcolor=[("disabled", GREEN_OFF)],
               background=[("active", GREEN_DK), ("disabled", GREEN_OFF)],
               foreground=[("disabled", GREEN_OFF_FG)])
        st.configure("Accent.TButton", padding=(12, 8), background=ACCENT, foreground="white", font=self.f_bold,
                     bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT, focuscolor=ACCENT)
        st.map("Accent.TButton", bordercolor=[("disabled", ACC_OFF)], lightcolor=[("disabled", ACC_OFF)], darkcolor=[("disabled", ACC_OFF)],
               background=[("active", ACC_ACT), ("disabled", ACC_OFF)],
               foreground=[("disabled", ACC_OFF_FG)])
        st.configure("Stop.TButton", padding=(12, 8), background=RED, foreground="white", font=self.f_bold,
                     bordercolor=RED, lightcolor=RED, darkcolor=RED, focuscolor=RED)
        st.map("Stop.TButton", bordercolor=[("disabled", RED_OFF)], lightcolor=[("disabled", RED_OFF)], darkcolor=[("disabled", RED_OFF)],
               background=[("active", RED_ACT), ("disabled", RED_OFF)],
               foreground=[("disabled", RED_OFF_FG)])
        st.configure("Treeview", rowheight=max(20, round(26 * self.scale)), background=CARD, fieldbackground=CARD, foreground=INK, borderwidth=0)
        st.configure("Treeview.Heading", font=self.f_bold, background=HEADING, foreground=INK, padding=(6, 5), relief="flat")
        st.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
        st.configure("Horizontal.TProgressbar", troughcolor=TROUGH, background=GREEN, thickness=14, borderwidth=0)
        st.configure("TPanedwindow", background=BG)
        st.configure("TEntry", fieldbackground=CARD, foreground=INK, insertcolor=INK)
        st.configure("TCombobox", fieldbackground=CARD, background=BTN, foreground=INK, arrowcolor=INK,
                     selectbackground=CARD, selectforeground=INK)
        st.map("TCombobox", fieldbackground=[("readonly", CARD)], foreground=[("readonly", INK)],
               selectbackground=[("readonly", CARD)], selectforeground=[("readonly", INK)])
        st.configure("TScrollbar", background=BTN, troughcolor=BG, arrowcolor=INK)
        st.map("TScrollbar", background=[("active", BTN_ACT)])
        st.configure("TScale", background=CARD, troughcolor=TROUGH)
        for opt, val in (("background", CARD), ("foreground", INK), ("selectBackground", ACCENT), ("selectForeground", "white")):
            self.root.option_add(f"*TCombobox*Listbox.{opt}", val)

    def _style_tags(self) -> None:
        """Cores das linhas das tabelas (mudam com o tema)."""
        if hasattr(self, "mod_tree"):
            self.mod_tree.tag_configure("done", background=DONE)
            self.mod_tree.tag_configure("part", background=PART)
        if hasattr(self, "tree"):
            self.tree.tag_configure("atencao", background=ATT)
            self.tree.tag_configure("revisada", background=REV)
            self.tree.tag_configure("ignorada", foreground=IGN)

    _COLOR_OPTS = ("background", "foreground", "highlightbackground", "highlightcolor", "activebackground",
                   "activeforeground", "insertbackground", "selectbackground", "selectforeground", "troughcolor")

    def apply_theme(self, choice: str) -> None:
        """Troca o tema na hora: recolore os widgets criados (cores antigas viram as novas) e refaz o estilo."""
        old = set_palette(choice)
        new = PALETTES[THEME]
        cmap = {old[k].lower(): new[k] for k in old if old[k].lower() != new[k].lower()}
        self.root.configure(bg=BG)
        self._style()
        self._recolor(self.root, cmap)
        self._style_tags()
        self._sync_galaxy()

    def _sync_galaxy(self) -> None:
        """Temas com efeito (Azul galáxia, Verde...): troca o título do topo por uma faixa animada; nos outros volta ao normal."""
        bar = getattr(self, "hdr_bar", None)
        if bar is None:
            return
        want = THEME if THEME in EFFECT_THEMES else None
        if self.galaxy is not None and getattr(self, "_fx_theme", None) != want:
            self.galaxy.destroy()
            self.galaxy = None
            if want is None:
                bar.pack_propagate(True)
                self.hdr_title.pack(side="left", padx=16, pady=10)
                self.hdr_sub.pack(side="left", padx=4)
        if want is not None and self.galaxy is None:
            from .galaxy import GalaxyBanner

            self.hdr_title.pack_forget()
            self.hdr_sub.pack_forget()
            self.galaxy = GalaxyBanner(bar, "Kenshi Quick Translator", self.hdr_sub.cget("text"), self.f_title,
                                       self.f_base, theme=want)
            self._fx_theme = want
            self.galaxy.place(x=0, y=0, relwidth=1, relheight=1)
            bar.configure(height=self.galaxy._h)
            bar.pack_propagate(False)
            tk.Misc.lower(self.galaxy)

    def _recolor(self, w, cmap: dict[str, str]) -> None:
        for c in [w, *w.winfo_children()]:
            if c is not w:
                self._recolor(c, cmap)
        if isinstance(w, ttk.Widget):
            if isinstance(w, ttk.Combobox):
                try:  # a lista que abre ao clicar é um widget à parte
                    pop = str(w.tk.call("ttk::combobox::PopdownWindow", str(w)))
                    w.tk.call(f"{pop}.f.l", "configure", "-background", CARD, "-foreground", INK)
                except tk.TclError:
                    pass
            return
        try:
            opts = w.keys()
        except tk.TclError:
            return
        for opt in self._COLOR_OPTS:
            if opt not in opts:
                continue
            try:
                val = str(w.cget(opt)).lower()
                if val in cmap:
                    w.configure(**{opt: cmap[val]})
                elif (isinstance(w, (tk.Text, tk.Listbox, tk.Entry)) and opt in ("background", "foreground", "insertbackground")
                      and not val.startswith("#")):
                    w.configure(**{opt: CARD if opt == "background" else INK})  # cores padrão do sistema
            except tk.TclError:
                pass

    # ================================================================ janela: posição, gaveta, atalhos
    def _restore_window(self) -> None:
        root = self.root
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        minsize = (min(900, sw - 40), min(560, sh - 90))
        root.minsize(*minsize)
        # padrão: cabe em telas pequenas (notebook de 1366x768), nunca maior que a tela
        root.geometry(f"{min(1400, sw - 40)}x{min(960, sh - 90)}")
        virtual = (root.winfo_vrootx(), root.winfo_vrooty(),
                   root.winfo_vrootwidth() or sw, root.winfo_vrootheight() or sh)
        saved = clamp_geometry(self.cfg.win_geometry, virtual, minsize)
        if saved:
            root.geometry(saved)
        if self.cfg.win_zoomed:
            try:
                root.state("zoomed")
            except tk.TclError:
                pass

    def _save_ui_state(self) -> None:
        """Guarda tamanho/posição da janela, mods selecionados, filtro e ordem da lista."""
        c = self.cfg
        try:
            state = self.root.state()
            c.win_zoomed = state == "zoomed"
            if state == "normal":  # maximizada: guarda só o "estava maximizada" e mantém o tamanho anterior
                c.win_geometry = self.root.geometry()
            if self._sel_restored:  # antes da primeira leitura da lista não há o que guardar: mantém o antigo
                c.last_selection = [str(self.entries[int(i)].path) for i in self.mod_tree.selection()]
            c.mod_filter = self._code_from(MODFILTER_LABEL, self.modfilter_var, "todos")
            c.mod_sort = self._code_from(MODSORT_LABEL, self.modsort_var, "padrao")
        except (tk.TclError, IndexError, ValueError):
            pass

    def _on_root_configure(self, event) -> None:
        if event.widget is not self.root:
            return
        narrow = event.width < NARROW_WIDTH
        if narrow != self._narrow:
            self._set_narrow(narrow)
        if self._wrap_after is None:
            self._wrap_after = self.root.after(150, self._rewrap)

    def _set_narrow(self, narrow: bool) -> None:
        """Janela estreita: a lista de mods sai do lado e vira uma gaveta (botão '☰ Mods' ou F9)."""
        self._narrow = narrow
        self._drawer_open = False
        self.sidebar.place_forget()
        panes = [str(p) for p in self.body_pane.panes()]
        if narrow:
            if str(self.sidebar) in panes:
                self.body_pane.forget(self.sidebar)
            self.btn_drawer.configure(text=i18n.tr("☰  Mods"))
            self.btn_drawer.pack(side="left", padx=(10, 0), pady=8)
        else:
            self.btn_drawer.pack_forget()
            if str(self.sidebar) not in panes:
                self.body_pane.insert(0, self.sidebar, weight=0)

    def toggle_drawer(self) -> None:
        if not self._narrow:
            return
        if self._drawer_open:
            self.sidebar.place_forget()
            self._drawer_open = False
            self.btn_drawer.configure(text=i18n.tr("☰  Mods"))
        else:
            width = min(440, max(300, self.root.winfo_width() - 80))
            self.sidebar.place(in_=self.body_pane, x=0, y=0, width=width, relheight=1.0)
            self.sidebar.lift()
            self._drawer_open = True
            self.btn_drawer.configure(text=i18n.tr("✕  Fechar lista"))

    def _rewrap(self) -> None:
        """Textos corridos de largura fixa acompanham a largura da janela."""
        self._wrap_after = None
        width = max(320, self.scroller.canvas.winfo_width() - 90)

        def walk(widget) -> None:
            for c in widget.winfo_children():
                if isinstance(c, (tk.Label, ttk.Label)):
                    try:
                        if int(str(c.cget("wraplength"))) >= 600:  # só os de largura inteira; os de coluna ficam
                            c.configure(wraplength=width)
                    except (tk.TclError, ValueError):
                        pass
                walk(c)

        walk(self.scroller.inner)

    def _escape(self) -> None:
        if self._stoppable and self._busy():
            self.stop()
        elif self._drawer_open:
            self.toggle_drawer()

    def _bind_shortcuts(self) -> None:
        r = self.root

        def on(seq: str, fn) -> None:
            r.bind(seq, lambda e: (fn(), "break")[1])

        on("<Control-t>", lambda: self.start_translate(False))
        on("<Control-T>", self.start_many)
        on("<F5>", lambda: self.refresh_mods(keep_selection=True))
        on("<F6>", self.build_mod)
        on("<F7>", self.install_mod)
        on("<F9>", self.toggle_drawer)
        on("<Control-Z>", self.undo_edit_ui)
        on("<Control-f>", lambda: self.query_entry.focus_set())
        on("<Control-F>", self.focus_mod_search)
        on("<Escape>", self._escape)
        for seq in ("<Control-equal>", "<Control-plus>", "<Control-KP_Add>"):
            on(seq, lambda: self.zoom(+1))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            on(seq, lambda: self.zoom(-1))
        on("<Control-0>", lambda: self.zoom(0))
        # Ctrl+T/Ctrl+Shift+T/Ctrl+F nos campos de texto trocariam letras (padrão do Tk): o atalho do programa vale
        for cls in ("Text", "Entry", "TEntry", "TCombobox"):
            r.bind_class(cls, "<Control-t>", lambda e: (self.start_translate(False), "break")[1])
            r.bind_class(cls, "<Control-T>", lambda e: (self.start_many(), "break")[1])
            r.bind_class(cls, "<Control-f>", lambda e: (self.query_entry.focus_set(), "break")[1])

    def focus_mod_search(self) -> None:
        if self._narrow and not self._drawer_open:
            self.toggle_drawer()
        self.mod_entry.focus_set()

    def show_shortcuts(self) -> None:
        lines = [f"{key:<17}{i18n.tr(desc)}" for key, desc in SHORTCUTS]
        messagebox.showinfo("Atalhos do teclado", "\n".join(lines))

    # ================================================================ partes da tela
    def _card(self, parent, number: str, title: str, expand: bool = False) -> ttk.Frame:
        box = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        box.pack(fill="both" if expand else "x", expand=expand, pady=(0, 10))
        head = tk.Frame(box, bg=CARD)
        head.pack(fill="x", padx=12, pady=(10, 4))
        if number:
            tk.Label(head, text=number, bg=ACCENT, fg="white", font=self.f_bold, width=2).pack(side="left")
        tk.Label(head, text=title, bg=CARD, fg=INK, font=self.f_big).pack(side="left", padx=(8 if number else 0, 0))
        inner = ttk.Frame(box, style="Card.TFrame")
        inner.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        inner.head = head  # type: ignore[attr-defined]
        self.cards[{"1": "one", "2": "how", "3": "review"}.get(number, number)] = box
        return inner

    def _fill_more_menu(self) -> None:
        """Monta o menu "Mais ações" na hora de abrir (assim já vem no idioma da interface)."""
        m = self.more_menu
        m.delete(0, "end")
        m.add_command(label=i18n.tr("Abrir pasta do mod"), command=self.open_mod_folder)
        m.add_command(label=i18n.tr("Abrir pasta dos projetos"), command=self.open_projects)
        m.add_separator()
        m.add_command(label=i18n.tr("Zerar tradução deste mod"), command=self.reset_selected)

    def _build_header(self) -> None:
        bar = tk.Frame(self.root, bg=HEAD)
        bar.pack(fill="x")
        self.hdr_bar = bar
        self.hdr_title = tk.Label(bar, text="Kenshi Quick Translator", bg=HEAD, fg="white", font=self.f_title)
        self.hdr_title.pack(side="left", padx=16, pady=10)
        self.hdr_sub = tk.Label(bar, text="traduza mods rapidamente", bg=HEAD, fg=HEADSUB, font=self.f_base)
        self.hdr_sub.pack(side="left", padx=4)
        self.galaxy = None
        self.btn_help = ttk.Button(bar, text="?  Ajuda",
                                   command=lambda: messagebox.showinfo("Como usar", i18n.help_text(HELP_TEXT)))
        self.btn_help.pack(side="right", padx=(4, 12), pady=8)
        self.btn_settings = ttk.Button(bar, text="⚙  Configurações", command=self.open_settings)
        self.btn_settings.pack(side="right", padx=4, pady=8)
        ttk.Button(bar, text="⌨  Atalhos", command=self.show_shortcuts).pack(side="right", padx=4, pady=8)
        self.btn_tutorial = ttk.Button(bar, text="▶  Tutorial", command=lambda: self.open_tutorial_menu(first_run=False))
        self.btn_tutorial.pack(side="right", padx=4, pady=8)
        self.btn_drawer = ttk.Button(bar, text="☰  Mods", command=self.toggle_drawer)  # só aparece em janela estreita

    def _build_body(self) -> None:
        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=10)
        self.body_pane = body
        left = ttk.Frame(body, width=430)
        self.sidebar = left
        self.scroller = scroller = ScrollFrame(body, BG)
        body.add(left, weight=0)
        body.add(scroller, weight=1)
        self._build_sidebar(left)
        self._build_main(scroller.inner)

    # ---------------------------------------------------------------- esquerda: mods
    def _build_sidebar(self, parent) -> None:
        box = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        self.cards["mods"] = box
        box.pack(fill="both", expand=True, padx=(0, 10))
        head = tk.Frame(box, bg=CARD)
        head.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(head, text="Seus mods", bg=CARD, fg=INK, font=self.f_big).pack(side="left")
        self.mods_count = tk.StringVar()
        tk.Label(head, textvariable=self.mods_count, bg=CARD, fg=MUTED, font=self.f_small).pack(side="right")

        sf = ttk.Frame(box, style="Card.TFrame")
        sf.pack(fill="x", padx=12, pady=4)
        self.mod_query = tk.StringVar()
        self.mod_query.trace_add("write", lambda *a: self.fill_mod_tree())
        ttk.Label(sf, text="Buscar:", style="Card.TLabel").pack(side="left")
        self.mod_entry = ttk.Entry(sf, textvariable=self.mod_query)
        self.mod_entry.pack(side="left", fill="x", expand=True, padx=6)

        ff = ttk.Frame(box, style="Card.TFrame")
        ff.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Label(ff, text="Mostrar:", style="Card.TLabel").pack(side="left")
        self.modfilter_var = tk.StringVar(value=i18n.tr(MODFILTER_LABEL["todos"]))
        mf = ttk.Combobox(ff, textvariable=self.modfilter_var, state="readonly", width=15,
                          values=[i18n.tr(v) for v in MODFILTER_LABEL.values()])
        mf.pack(side="left", padx=(4, 8))
        mf.bind("<<ComboboxSelected>>", lambda e: self.fill_mod_tree())
        ttk.Label(ff, text="Ordem:", style="Card.TLabel").pack(side="left")
        self.modsort_var = tk.StringVar(value=i18n.tr(MODSORT_LABEL["padrao"]))
        ms = ttk.Combobox(ff, textvariable=self.modsort_var, state="readonly", width=22,
                          values=[i18n.tr(v) for v in MODSORT_LABEL.values()])
        ms.pack(side="left", padx=4)
        ms.bind("<<ComboboxSelected>>", lambda e: self.fill_mod_tree())

        mid = ttk.Frame(box, style="Card.TFrame")
        mid.pack(fill="both", expand=True, padx=12, pady=4)
        self.mod_tree = ttk.Treeview(mid, columns=("idioma", "prog", "onde"), show="tree headings", selectmode="extended")
        self.mod_tree.heading("#0", text="Mod")
        self.mod_tree.column("#0", width=190, anchor="w")
        for c, t, w in (("idioma", "Idioma", 110), ("prog", "Feito", 52), ("onde", "Onde", 74)):
            self.mod_tree.heading(c, text=t)
            self.mod_tree.column(c, width=w, anchor="w" if c != "prog" else "center")
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.mod_tree.yview)
        self.mod_tree.configure(yscrollcommand=sb.set)
        self.mod_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._style_tags()
        self.mod_tree.bind("<<TreeviewSelect>>", self.on_mod_select)
        self.mod_tree.bind("<Motion>", self._hover_mod)
        self.mod_tree.bind("<Leave>", lambda e: self._show_mod_path())
        self.mod_path_var = tk.StringVar(value="")
        self._refill_after = None
        tk.Label(box, textvariable=self.mod_path_var, bg=CARD, fg=MUTED, font=self.f_small, wraplength=400,
                 justify="left", anchor="w").pack(fill="x", padx=12)

        self.empty_hint = tk.Label(
            box, bg=CARD, fg=MUTED, font=self.f_small, wraplength=380, justify="left",
            text="Não achei o Kenshi sozinho. Clique em “Pasta do Kenshi…” ou use “Abrir arquivo…”.")
        self.game_info = tk.StringVar()
        tk.Label(box, textvariable=self.game_info, bg=CARD, fg=MUTED, font=self.f_small, wraplength=400,
                 justify="left").pack(fill="x", padx=12)
        self.empty_hint.pack(fill="x", padx=12)

        bb = ttk.Frame(box, style="Card.TFrame")  # botões em grade: nenhum fica cortado na barra estreita
        bb.pack(fill="x", padx=12, pady=(6, 6))
        self.tt["mod_buttons"] = bb
        bb.columnconfigure(0, weight=1)
        bb.columnconfigure(1, weight=1)
        ttk.Button(bb, text="⟳ Atualizar (F5)", command=self.refresh_mods).grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=2)
        ttk.Button(bb, text="+  Abrir arquivo…", command=self.pick_file).grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=2)
        ttk.Button(bb, text="⌂  Pasta do Kenshi…", command=self.pick_kenshi).grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=2)
        # o que se usa pouco fica no menu "Mais": a barra estreita fica com 4 botões em vez de 7
        self.more_menu = tk.Menu(bb, tearoff=0, postcommand=self._fill_more_menu, bg=CARD, fg=INK,
                                 activebackground=ACCENT, activeforeground="white", relief="flat", bd=1)
        self.btn_more = ttk.Menubutton(bb, text="Mais ações", menu=self.more_menu, direction="below")
        self.btn_more.grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=2)
        ttk.Button(bb, text="→  Copiar mod para a pasta do jogo", command=self.copy_to_game).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(box, text="Dica: Ctrl+clique escolhe vários mods para traduzir em fila.", bg=CARD, fg=MUTED,
                 font=self.f_small).pack(anchor="w", padx=12, pady=(0, 10))

    # ---------------------------------------------------------------- direita
    def _build_main(self, parent) -> None:
        # ---- 1. mod escolhido
        c1 = self._card(parent, "1", "Mod escolhido")
        self.mod_var = tk.StringVar(value="Nenhum mod aberto")
        ttk.Label(c1, textvariable=self.mod_var, style="Bold.TLabel").pack(side="left", anchor="n")
        self.info_var = tk.StringVar(value="Clique em um mod na lista da esquerda para começar.")
        self.info_label = tk.Label(c1, textvariable=self.info_var, bg=CARD, fg=MUTED, font=self.f_base,
                                   justify="left", anchor="w", wraplength=600)
        self.info_label.pack(side="left", fill="x", expand=True, anchor="n", padx=(14, 0))

        # ---- 2. como traduzir
        c2 = self._card(parent, "2", "Como traduzir")
        cols = ttk.Frame(c2, style="Card.TFrame")
        cols.pack(fill="x")
        left = ttk.Frame(cols, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 18))
        right = ttk.Frame(cols, style="Card.TFrame")
        right.pack(side="left", fill="both", expand=True)

        # Opções avançadas: recolhidas por padrão, para o essencial (idioma, serviço, Traduzir) ficar limpo
        advbar = ttk.Frame(c2, style="Card.TFrame")
        advbar.pack(fill="x", pady=(8, 0))
        self.adv_btn = ttk.Button(advbar, text="▸  Opções avançadas", command=self.toggle_advanced)
        self.adv_btn.pack(side="left")
        self.adv_summary_var = tk.StringVar()
        ttk.Label(advbar, textvariable=self.adv_summary_var, style="Muted.TLabel").pack(side="left", padx=10)
        self.adv_frame = ttk.Frame(c2, style="Card.TFrame")
        advl = ttk.Frame(self.adv_frame, style="Card.TFrame")
        advl.pack(side="left", fill="both", expand=True, padx=(0, 18), pady=(6, 0))
        advr = ttk.Frame(self.adv_frame, style="Card.TFrame")
        advr.pack(side="left", fill="both", expand=True, pady=(6, 0))
        self.adv_open = False

        self.src_var, self.dst_var = tk.StringVar(), tk.StringVar()
        self.prov_var, self.key_var, self.url_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.names_var = tk.BooleanVar(value=True)
        self.multi_var = tk.BooleanVar(value=False)
        self.workers_var = tk.IntVar(value=3)
        self.install_var = tk.BooleanVar(value=False)
        self.src_checks = {code: tk.BooleanVar(value=False) for code in MULTI_CHOICES}
        self.src_check_widgets: dict[str, ttk.Checkbutton] = {}

        # esquerda: idiomas
        g = ttk.Frame(left, style="Card.TFrame")
        g.pack(fill="x")
        self.tt["langs"] = g
        ttk.Label(g, text="Idioma do mod:", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=3)
        self.src_box = ttk.Combobox(g, textvariable=self.src_var, state="readonly", width=28,
                                    values=[lang_display(c) for c in LANGUAGES])
        self.src_box.grid(row=0, column=1, sticky="w", padx=8, pady=3)
        ttk.Label(g, text="Traduzir para:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=3)
        self.dst_box = ttk.Combobox(g, textvariable=self.dst_var, state="readonly", width=28,
                                    values=[lang_display(c) for c in LANGUAGES if c != "auto"])
        self.dst_box.grid(row=1, column=1, sticky="w", padx=8, pady=3)
        self.src_box.bind("<<ComboboxSelected>>", self.on_languages)
        self.dst_box.bind("<<ComboboxSelected>>", self.on_languages)
        self.gloss_var = tk.StringVar()
        self._gloss_lang_seen = self.cfg.target_lang  # para só perguntar quando o IDIOMA DE DESTINO muda
        ttk.Label(g, text="Glossário:", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Label(g, textvariable=self.gloss_var, style="Muted.TLabel").grid(row=2, column=1, sticky="w", padx=8, pady=3)

        ttk.Checkbutton(advl, text="Este mod tem mais de um idioma (ex.: inglês e chinês)", variable=self.multi_var,
                        style="Card.TCheckbutton", command=self.on_multi_toggle).pack(anchor="w", pady=(0, 2))
        self.multi_frame = ttk.Frame(advl, style="Card.TFrame")
        ttk.Label(self.multi_frame, text="Idiomas que o mod tem (cada texto é identificado sozinho):",
                  style="Muted.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        for i, code in enumerate(MULTI_CHOICES):
            cb = ttk.Checkbutton(self.multi_frame, text=lang_name(code, i18n.language()), variable=self.src_checks[code],
                                 style="Card.TCheckbutton", command=self.on_sources_changed)
            cb.grid(row=1 + i // 4, column=i % 4, sticky="w", padx=(0, 12))
            cb._tip_text = TIP_MULTI_LANG
            self.src_check_widgets[code] = cb
        ttk.Checkbutton(advl, text="Não traduzir nomes de personagens", variable=self.names_var,
                        style="Card.TCheckbutton", command=self._adv_summary).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(advl, text="Instalar no jogo ao terminar (fila)", variable=self.install_var,
                        style="Card.TCheckbutton", command=self._adv_summary).pack(anchor="w", pady=(6, 0))

        # direita: serviço e velocidade
        r = ttk.Frame(right, style="Card.TFrame")
        r.pack(fill="x")
        self.tt["service"] = r
        ttk.Label(r, text="Serviço:", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=3)
        self.prov_box = ttk.Combobox(r, textvariable=self.prov_var, state="readonly", width=30,
                                     values=[s.label for s in SPECS])
        self.prov_box.grid(row=0, column=1, columnspan=2, sticky="w", padx=8, pady=3)
        self.prov_box.bind("<<ComboboxSelected>>", self.on_provider)
        self.key_label = ttk.Label(r, text="Chave:", style="Card.TLabel")
        self.key_entry = ttk.Entry(r, textvariable=self.key_var, show="•", width=30)
        self.key_label.grid(row=1, column=0, sticky="w", pady=3)
        self.key_entry.grid(row=1, column=1, sticky="w", padx=8, pady=3)
        self.url_label = ttk.Label(r, text="Servidor:", style="Card.TLabel")
        self.url_entry = ttk.Entry(r, textvariable=self.url_var, width=30)
        self.key_hint = tk.Label(r, text="Mais de uma chave? Separe com ;  (divide o trabalho entre elas)",
                                 bg=CARD, fg=MUTED, font=self.f_small, anchor="w")
        self.key_hint.grid(row=3, column=0, columnspan=3, sticky="w", padx=0, pady=(0, 2))
        self.url_label.grid(row=2, column=0, sticky="w", pady=3)
        self.url_entry.grid(row=2, column=1, sticky="w", padx=8, pady=3)
        ttk.Button(r, text="Testar serviço", command=self.test_provider).grid(row=0, column=3, padx=(4, 14))
        self.svc_btn = ttk.Button(r, text="Serviços do agregado (IAs, DeepL, Google Cloud)…", command=self.open_services)
        self.svc_btn.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 2))

        sp = ttk.Frame(advr, style="Card.TFrame")
        sp.pack(fill="x", pady=(8, 0))
        self.tt["speed"] = sp
        ttk.Label(sp, text="Velocidade:", style="Card.TLabel").pack(side="left")
        self.speed_scale = ttk.Scale(sp, from_=1, to=12, orient="horizontal", length=170,
                                     command=self.on_speed)
        self.speed_scale.pack(side="left", padx=8)
        self.speed_label = ttk.Label(sp, text="3 partes ao mesmo tempo", style="Bold.TLabel")
        self.speed_label.pack(side="left")
        self.speed_hint = tk.Label(advr, bg=CARD, fg=MUTED, font=self.f_small, justify="left", anchor="w",
                                   wraplength=420,
                                   text="Cada parte é um pedido ao serviço. Mais partes = mais rápido, até o limite do "
                                        "serviço. Se ele reclamar, o programa diminui sozinho.")
        self.speed_hint.pack(fill="x", anchor="w")

        # barra de ações
        self._adv_sep = ttk.Separator(c2, orient="horizontal")
        self._adv_sep.pack(fill="x", pady=8)
        act = ttk.Frame(c2, style="Card.TFrame")
        act.pack(fill="x")
        self.tt["actions"] = act
        self.btn_translate = ttk.Button(act, text="▶  Traduzir este mod  (Ctrl+T)", style="Primary.TButton",
                                        command=lambda: self.start_translate(False))
        self.btn_translate.pack(side="left")
        self.tt["go"] = self.btn_translate
        self.btn_many = ttk.Button(act, text="▶▶  Traduzir selecionados  (Ctrl+Shift+T)", style="Accent.TButton",
                                   command=self.start_many)
        self.btn_many.pack(side="left", padx=8)
        self.btn_stop = ttk.Button(act, text="■  Parar  (Esc)", style="Stop.TButton", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left")
        act2 = ttk.Frame(c2, style="Card.TFrame")  # segunda linha: cabe em janelas estreitas
        act2.pack(fill="x", pady=(8, 0))
        self.tt["actions2"] = act2
        self.btn_redo = ttk.Button(act2, text="Refazer automáticas", command=lambda: self.start_translate(True))
        self.btn_redo.pack(side="left")
        self.btn_second = ttk.Button(act2, text="Segunda passada nos “Conferir”…", command=self.second_pass_ui)
        self.btn_second.pack(side="left", padx=6)

        prog = ttk.Frame(c2, style="Card.TFrame")  # barra + status + gráfico + luzes dos serviços
        prog.pack(fill="x", pady=(8, 0))
        self.tt["progress"] = prog
        pb = ttk.Frame(prog, style="Card.TFrame")
        pb.pack(fill="x")
        self.progress = ttk.Progressbar(pb, mode="determinate")
        self.progress.pack(fill="x")
        self.status_var = tk.StringVar(value="Escolha um mod na lista para começar.")
        self.eta_var = tk.StringVar(value="")
        line = ttk.Frame(prog, style="Card.TFrame")
        line.pack(fill="x", pady=(4, 0))
        ttk.Label(line, textvariable=self.status_var, style="Card.TLabel").pack(side="left")
        ttk.Label(line, textvariable=self.eta_var, style="Muted.TLabel").pack(side="right")
        self.spark = tk.Canvas(line, width=150, height=30, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.spark.pack(side="right", padx=(0, 10))
        Tip(self.spark, self._spark_tip)
        self.svc_var = tk.StringVar(value="")  # (a linha de texto foi trocada pelas luzes; mantida vazia)
        self.notice_var = tk.StringVar(value="")
        self._live_provider = None
        self.svc_frame = ttk.Frame(prog, style="Card.TFrame")
        self.svc_frame.pack(fill="x")
        self._svc_widgets: dict[str, tuple[tk.Label, tk.Label]] = {}
        self._svc_info: dict[str, str] = {}
        ttk.Label(c2, textvariable=self.notice_var, style="Bold.TLabel", wraplength=640, justify="left").pack(fill="x")
        self.session.on_message = lambda m: self.events.put(("notice", m))

        # ---- 3. revisar e gerar
        c3 = self._card(parent, "3", "Revise e gere o mod", expand=True)
        flt = ttk.Frame(c3, style="Card.TFrame")
        flt.pack(fill="x")
        self.tt["filters"] = flt
        ttk.Label(flt, text="Mostrar:", style="Card.TLabel").pack(side="left")
        self.filter_var = tk.StringVar(value=i18n.tr(FILTER_LABEL["todos"]))
        fbox = ttk.Combobox(flt, textvariable=self.filter_var, state="readonly", width=14,
                            values=[i18n.tr(v) for v in FILTER_LABEL.values()])
        fbox.pack(side="left", padx=6)
        fbox.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())
        self.filter_box = fbox
        self.lang_var = tk.StringVar(value=i18n.tr("Todos os idiomas"))
        self.lang_box = ttk.Combobox(flt, textvariable=self.lang_var, state="readonly", width=22)  # só aparece com 2+ idiomas
        self.lang_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())
        ttk.Label(flt, text="Buscar:", style="Card.TLabel").pack(side="left", padx=(10, 0))
        self.query_var = tk.StringVar()
        self.query_var.trace_add("write", lambda *a: self._debounced_table())
        self.query_entry = ttk.Entry(flt, textvariable=self.query_var, width=26)
        self.query_entry.pack(side="left", padx=6)
        self.stats_var = tk.StringVar()
        ttk.Label(flt, textvariable=self.stats_var, style="Muted.TLabel").pack(side="right")

        mid = ttk.Frame(c3, style="Card.TFrame")
        mid.pack(fill="both", expand=True, pady=(6, 0))
        self.tt["table"] = mid
        self.tree = ttk.Treeview(mid, columns=("estado", "idioma", "original", "traducao"), show="headings",
                                 selectmode="browse", height=5)
        for c, title, w in (("estado", "Estado", 86), ("idioma", "Idioma", 78), ("original", "Original", 360),
                            ("traducao", "Tradução", 360)):
            self.tree.heading(c, text=title)
            self.tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        self._style_tags()
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self._set_idioma_column(False)

        ed = ttk.Frame(c3, style="Card.TFrame")
        ed.pack(fill="x", pady=(8, 0))
        self.tt["editor"] = ed
        lf = ttk.Frame(ed, style="Card.TFrame")
        lf.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ttk.Label(lf, text="Original", style="Muted.TLabel").pack(anchor="w")
        self.src_text = tk.Text(lf, height=4, wrap="word", state="disabled", background=SRC, foreground=INK, insertbackground=INK, relief="flat",
                                highlightthickness=1, highlightbackground=LINE, padx=6, pady=4)
        self.src_text.pack(fill="both", expand=True)
        rf = ttk.Frame(ed, style="Card.TFrame")
        rf.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ttk.Label(rf, text="Tradução (edite aqui)", style="Muted.TLabel").pack(anchor="w")
        self.dst_text = tk.Text(rf, height=4, wrap="word", relief="flat", highlightthickness=1,
                                background=CARD, foreground=INK, insertbackground=INK,
                                highlightbackground=LINE, highlightcolor=ACCENT, padx=6, pady=4)
        self.dst_text.pack(fill="both", expand=True)
        self.dst_text.bind("<KeyRelease>", lambda e: self.validate_editor())
        self.setup_marker_tags()

        eb = ttk.Frame(c3, style="Card.TFrame")
        eb.pack(fill="x", pady=(6, 0))
        self.tt["editbtns"] = eb
        self.check_var = tk.StringVar(value="")
        self.check_label = tk.Label(eb, textvariable=self.check_var, bg=CARD, fg=MUTED, font=self.f_bold)
        self.check_label.pack(side="left")
        self.ctx_var = tk.StringVar(value="")
        tk.Label(eb, textvariable=self.ctx_var, bg=CARD, fg=MUTED, font=self.f_small).pack(side="left", padx=12)
        ttk.Button(eb, text="✓  Aplicar e próximo (Ctrl+Enter)", command=self.apply_edit).pack(side="right")
        ttk.Button(eb, text="Copiar original", command=self.copy_source).pack(side="right", padx=6)
        ttk.Button(eb, text="↶ Desfazer edição", command=self.undo_edit_ui).pack(side="right")

        ob = ttk.Frame(c3, style="Card.TFrame")  # linha de baixo: o que gera/instala o mod
        ob.pack(fill="x", pady=(10, 0))
        self.tt["build"] = ob
        ob2 = ttk.Frame(c3, style="Card.TFrame")  # linha de cima: glossário, ferramentas e arquivos PO
        ob2.pack(fill="x", pady=(6, 0))
        self.tt["tools"] = ob2
        self.btn_build = ttk.Button(ob, text="Gerar mod de tradução…  (F6)", style="Accent.TButton", command=self.build_mod)
        self.btn_build.pack(side="left")
        self.btn_install = ttk.Button(ob, text="⬇  Instalar no jogo  (F7)", style="Accent.TButton", command=self.install_mod)
        self.btn_install.pack(side="left", padx=8)
        self.btn_restore = ttk.Button(ob, text="↶  Restaurar o original", command=self.restore_original_ui)
        self.btn_restore.pack(side="left")
        ttk.Button(ob2, text="Glossário…", command=self.open_glossary).pack(side="left")
        ttk.Button(ob2, text="Ferramentas…", command=self.open_tools).pack(side="left", padx=6)
        ttk.Button(ob2, text="Modo simples", command=self.open_simple).pack(side="left")
        ttk.Button(ob2, text="Exportar PO…", command=self.export_po).pack(side="left", padx=6)
        ttk.Button(ob2, text="Importar PO…", command=self.import_po).pack(side="left")

        # Em janela baixa, quem encolhe é a tabela: editor e botões de baixo têm prioridade de espaço.
        for frame, pad in ((ob, (6, 0)), (ob2, (10, 0)), (eb, (6, 0)), (ed, (8, 0))):
            frame.pack_forget()
            frame.pack(side="bottom", fill="x", pady=pad)
        mid.pack_forget()
        mid.pack(side="top", fill="both", expand=True, pady=(6, 0))

    # ================================================================ configuração
    def _fill_from_config(self) -> None:
        c = self.cfg
        self.modfilter_var.set(i18n.tr(MODFILTER_LABEL.get(c.mod_filter, MODFILTER_LABEL["todos"])))
        self.modsort_var.set(i18n.tr(MODSORT_LABEL.get(c.mod_sort, MODSORT_LABEL["padrao"])))
        self.src_var.set(lang_display(c.source_lang if c.source_lang in LANGUAGES else "auto"))
        self.dst_var.set(lang_display(c.target_lang if c.target_lang in LANGUAGES else "pt-BR"))
        self.refresh_glossary_label()
        self.prov_var.set(next((s.label for s in SPECS if s.key == c.provider), SPECS[0].label))
        self.key_var.set(c.api_key)
        self.url_var.set(c.server_url)
        self.names_var.set(c.keep_character_names)
        self.multi_var.set(c.multi_source)
        for code, var in self.src_checks.items():
            var.set(code in c.source_langs)
        w = max(1, min(12, int(c.workers)))
        self.workers_var.set(w)
        self.speed_scale.set(w)
        self.on_speed(w)
        self.on_provider()
        self.on_multi_toggle(initial=True)

    @staticmethod
    def _code_from_display(text: str) -> str:
        for code in LANGUAGES:
            if lang_display(code) == text:
                return code
        return "auto"

    def _sync_cfg(self) -> None:
        c = self.cfg
        c.source_lang = self._code_from_display(self.src_var.get())
        c.target_lang = self._code_from_display(self.dst_var.get()) or "pt-BR"
        if c.target_lang == "auto":
            c.target_lang = "pt-BR"
        c.provider = next((s.key for s in SPECS if s.label == self.prov_var.get()), SPECS[0].key)
        c.api_key = self.key_var.get().strip()
        c.server_url = self.url_var.get().strip()
        c.keep_character_names = bool(self.names_var.get())
        c.multi_source = bool(self.multi_var.get())
        c.source_langs = [code for code, var in self.src_checks.items() if var.get()]
        c.workers = max(1, min(12, int(round(float(self.speed_scale.get())))))
        c.save()

    def on_provider(self, event=None) -> None:
        spec = next((s for s in SPECS if s.label == self.prov_var.get()), SPECS[0])
        for w in (self.key_label, self.key_entry, self.key_hint):
            (w.grid if spec.needs_key else w.grid_remove)()
        for w in (self.url_label, self.url_entry):
            (w.grid if spec.needs_url else w.grid_remove)()
        (self.svc_btn.grid if spec.key == "agregado" else self.svc_btn.grid_remove)()
        if spec.key in ("agregado", "google-free", "google2", "bing", "microsoft", "yandex"):
            self.speed_hint.configure(
                text="Serviços gratuitos limitam os pedidos: o programa já espaça e troca de serviço sozinho. Use 2 ou 3 partes.")
        else:
            self.speed_hint.configure(
                text="Cada parte é um pedido ao serviço. Mais partes = mais rápido, até o limite do serviço. "
                     "Se ele reclamar, o programa diminui sozinho.")

    def on_speed(self, value=None) -> None:
        n = max(1, min(12, int(round(float(value if value is not None else self.speed_scale.get())))))
        self.speed_label.configure(text=f"{n} parte{'s' if n > 1 else ''} ao mesmo tempo")
        self._adv_summary()

    def toggle_advanced(self, open_: bool | None = None) -> None:
        """Abre ou fecha o quadro "Opções avançadas" (velocidade, vários idiomas, nomes, instalar ao terminar)."""
        want = (not self.adv_open) if open_ is None else bool(open_)
        if want == self.adv_open:
            return
        self.adv_open = want
        if want:
            self.adv_frame.pack(fill="x", before=self._adv_sep)
        else:
            self.adv_frame.pack_forget()
        self.adv_btn.configure(text=i18n.tr("▾  Opções avançadas" if want else "▸  Opções avançadas"))
        self._adv_summary()

    def expand_advanced_for(self, target) -> None:
        """Usado pelo tutorial: se a parte explicada está dentro das opções avançadas, abre o quadro."""
        w = target
        while w is not None:
            if w is self.adv_frame:
                self.toggle_advanced(True)
                self.root.update_idletasks()
                return
            w = getattr(w, "master", None)

    def _adv_summary(self) -> None:
        """Resumo ao lado do botão (só aparece com o quadro fechado): o que está ligado lá dentro."""
        if self.adv_open:
            self.adv_summary_var.set("")
            return
        tr = i18n.tr
        try:
            n = max(1, min(12, int(round(float(self.speed_scale.get())))))
        except (tk.TclError, ValueError):
            n = 3
        parts = [f"{tr('velocidade')} {n}", tr("nomes preservados" if self.names_var.get() else "nomes traduzidos")]
        if self.multi_var.get():
            parts.append(tr("vários idiomas"))
        if self.install_var.get():
            parts.append(tr("instala ao terminar"))
        self.adv_summary_var.set("  ·  ".join(parts))

    def on_multi_toggle(self, initial: bool = False) -> None:
        multi = bool(self.multi_var.get())
        if multi:
            self.multi_frame.pack(fill="x", pady=(2, 0), after=self._multi_anchor())
            if not any(v.get() for v in self.src_checks.values()):
                for code in present_languages(self.counts) or ["en"]:
                    if code in self.src_checks:
                        self.src_checks[code].set(True)
            self.src_box.configure(state="disabled")
        else:
            self.multi_frame.pack_forget()
            self.src_box.configure(state="readonly")
        self._set_idioma_column(multi)
        if multi and not initial:
            self.toggle_advanced(True)  # a lista de idiomas vive no quadro avançado
        self._adv_summary()
        if not initial and self.session.project is not None:
            self.refresh_table()

    def _multi_anchor(self):
        # o quadro dos idiomas fica logo abaixo da caixinha "mais de um idioma"
        for child in self.multi_frame.master.pack_slaves():
            if isinstance(child, ttk.Checkbutton):
                return child
        return None

    def on_sources_changed(self) -> None:
        pass  # só lido na hora de traduzir

    def on_languages(self, event=None) -> None:
        """Trocar o idioma de destino abre outro projeto do mesmo mod (cada um guarda o seu)."""
        try:
            self._sync_cfg()
            dst_changed = self.cfg.target_lang != self._gloss_lang_seen
            self._gloss_lang_seen = self.cfg.target_lang
            if self.session.mod_path is not None and not self._busy():
                self.load_mod(self.session.mod_path, force=True)
            self.refresh_mods(keep_selection=True)
            self.refresh_glossary_label()
            if dst_changed and not self._busy():
                self._glossary_checkpoint(gate=False)  # idioma novo sem glossário: pergunta o que fazer
        except Exception as e:  # noqa: BLE001 - erro vira aviso na tela, nunca fecha o programa
            self.last_error = format_exc(type(e), e, e.__traceback__)
            log_error(self.last_error)
            self.status_var.set(f"Erro ao trocar o idioma: {type(e).__name__}: {e}")

    def refresh_glossary_label(self) -> None:
        """Mostra qual glossário vale agora (o do idioma de destino) e quantos termos tem."""
        try:
            self.session.reload_glossary()
            lang = self.session.glossary_lang
            nome = LANGUAGES.get(lang, lang)
            if self.session.glossary_offer() is not None:
                txt = f"{nome}: ainda não tem (será oferecido ao traduzir)"
            elif not self.session.glossary.terms:
                txt = f"{nome}: vazio"
            else:
                txt = f"{nome}: {len(self.session.glossary.terms)} termos"
            self.gloss_var.set(i18n.tr(txt))
        except Exception:  # noqa: BLE001
            pass

    def _glossary_checkpoint(self, gate: bool) -> bool:
        """Se o idioma de destino não tem glossário, pergunta antes. Devolve False se a pessoa cancelou a tradução."""
        try:
            self.session.reload_glossary()
            offer = self.session.glossary_offer()
        except Exception:  # noqa: BLE001
            return True
        if offer is None:
            return True
        dlg = GlossaryOfferDialog(self.root, self.session, offer, gate)
        self.root.wait_window(dlg.win)
        self.refresh_glossary_label()
        return dlg.result != "cancel"

    def _set_idioma_column(self, show: bool) -> None:
        cols = ("estado", "idioma", "original", "traducao") if show else ("estado", "original", "traducao")
        self.tree.configure(displaycolumns=cols)

    # ================================================================ lista de mods
    def refresh_mods(self, keep_selection: bool = False) -> None:
        """Lê a pasta do jogo e mostra os mods; idioma e progresso chegam em segundo plano."""
        keep_paths = {self.entries[int(i)].path for i in self.mod_tree.selection()} if keep_selection else set()
        dirs = self.session.locate_game()
        found = self.session.installed_mods() if dirs.kenshi else []
        extra = [e for e in self.entries if e.source == "avulso" and e.path not in {f.path for f in found}]
        if not self._sel_restored:  # mod aberto por "Abrir arquivo…" na última vez também volta
            known = {f.path for f in found} | {e.path for e in extra}
            for p in self.cfg.last_selection:
                pp = Path(p)
                if pp not in known and pp.suffix.lower() == ".mod" and pp.is_file():
                    extra.append(ModEntry(pp.name, pp, "avulso", pp.stat().st_size))
                    known.add(pp)
        self.entries = found + extra
        if dirs.kenshi:
            self.game_info.set(f"Kenshi: {dirs.kenshi}" + (f"  ({dirs.how})" if dirs.how else ""))
        else:
            self.game_info.set("")
        self.mod_gen += 1
        self.labels: dict[int, tuple[str, str]] = {}
        self.mod_counts: dict[int, dict[str, int] | None] = {}
        self.fill_mod_tree()
        if keep_paths:
            for iid in self.mod_tree.get_children():
                if self.entries[int(iid)].path in keep_paths:
                    self.mod_tree.selection_add(iid)
        if not self._sel_restored and self.entries:
            self._sel_restored = True
            want = set(self.cfg.last_selection)
            iids = [iid for iid in self.mod_tree.get_children() if str(self.entries[int(iid)].path) in want]
            if iids:
                self.mod_tree.selection_set(iids)
                self.mod_tree.see(iids[0])
        gen = self.mod_gen
        entries = list(self.entries)
        threading.Thread(target=self._load_mod_info, args=(gen, entries), daemon=True).start()

    def _load_mod_info(self, gen: int, entries: list[ModEntry]) -> None:
        for i, e in enumerate(entries):
            if gen != self.mod_gen:
                return
            try:
                label = dict(self.session.mod_profile(e.path))  # contagem por idioma; o texto é montado ao exibir
            except Exception:  # noqa: BLE001
                label = None
            prog = self.session.saved_progress(e.path)
            self.events.put(("mod_info", gen, i, label, prog))

    def _mod_lang_text(self, counts: dict[str, int] | None) -> str:
        """Texto da coluna Idioma da lista de mods, no idioma atual do programa."""
        if counts is None:
            return i18n.tr("não consegui ler")
        return language_label(counts, i18n.language())

    def relabel_languages(self) -> None:
        """Depois de trocar o idioma do programa: refaz os nomes de idioma que já estavam na tela."""
        for i, counts in list(self.mod_counts.items()):
            old = self.labels.get(i)
            if old is not None:
                self.labels[i] = (self._mod_lang_text(counts), old[1])
                if self.mod_tree.exists(str(i)):
                    self.mod_tree.set(str(i), "idioma", self.labels[i][0])
        for code, cb in self.src_check_widgets.items():
            cb.configure(text=lang_name(code, i18n.language()))
        if self.session.project is not None:
            self.refresh_table()
            if getattr(self, "counts", None) is not None:
                self._show_counts(self.counts)

    def _code_from(self, table: dict, var: tk.StringVar, default: str) -> str:
        for code, label in table.items():
            if i18n.tr(label) == var.get():
                return code
        return default

    def _mod_pct(self, i: int) -> int | None:
        """Percentual já feito do mod i; None se o programa ainda não leu (a leitura é em segundo plano)."""
        got = getattr(self, "labels", {}).get(i)
        if got is None:
            return None
        text = got[1]
        return int(text[:-1]) if text.endswith("%") and text[:-1].isdigit() else 0

    def _mod_visible(self, i: int, e: ModEntry, q: str, flt: str) -> bool:
        if q and q not in e.name.casefold():
            return False
        if flt == "workshop":
            return e.source == "workshop"
        if flt == "local":
            return e.source == "local"
        if flt in ("sem", "incompleto", "completo"):
            pct = self._mod_pct(i)
            if pct is None:
                return False
            return (pct == 0) if flt == "sem" else (0 < pct < 100) if flt == "incompleto" else pct >= 100
        return True

    def fill_mod_tree(self) -> None:
        sel = {self.entries[int(i)].path for i in self.mod_tree.selection()} if self.entries else set()
        q = self.mod_query.get().strip().casefold()
        flt = self._code_from(MODFILTER_LABEL, self.modfilter_var, "todos")
        order = self._code_from(MODSORT_LABEL, self.modsort_var, "padrao")
        idx = [i for i, e in enumerate(self.entries) if self._mod_visible(i, e, q, flt)]
        if order == "nome":
            idx.sort(key=lambda i: self.entries[i].name.casefold())
        elif order == "tamanho":
            idx.sort(key=lambda i: -self.entries[i].size)
        elif order in ("menos", "mais"):
            sign = 1 if order == "menos" else -1
            # mods ainda não lidos vão para o fim
            idx.sort(key=lambda i: (self._mod_pct(i) is None, sign * (self._mod_pct(i) or 0),
                                    self.entries[i].name.casefold()))
        repeated = {n for n in (e.name.casefold() for e in self.entries)
                    if sum(1 for x in self.entries if x.name.casefold() == n) > 1}
        self.mod_tree.delete(*self.mod_tree.get_children())
        for i in idx:
            e = self.entries[i]
            label, prog = getattr(self, "labels", {}).get(i, ("…", ""))
            tags = ()
            if prog.endswith("%"):
                tags = ("done",) if prog == "100%" else ("part",) if prog != "0%" else ()
            shown_name = e.name
            if e.name.casefold() in repeated:  # mesmo nome em dois lugares: mostra de onde é cada um
                shown_name = f"{e.name}  [{i18n.tr(SOURCE_LABEL.get(e.source, e.source))}]"
            self.mod_tree.insert("", "end", iid=str(i), text=shown_name, image=self._icons.get(e.path) or "",
                                 values=(label, prog, i18n.tr(SOURCE_LABEL.get(e.source, e.source))), tags=tags)
            self._icon_iids[e.path] = str(i)
            if e.path not in self._icons and all(p != e.path for p, _ in self._icon_todo):
                self._icon_todo.append((e.path, e.source))
            if e.path in sel:
                self.mod_tree.selection_add(str(i))
        self._schedule_icons()
        shown, total = len(idx), len(self.entries)
        self.mods_count.set(f"{shown} de {total}" if shown != total else f"{total} mods")  # (i18n.PATTERNS traduz)
        if self.entries:
            self.empty_hint.pack_forget()
        else:
            self.empty_hint.pack(fill="x", padx=12)

    # ---------------------------------------------------------------- ícones dos mods
    def _icon_px(self) -> int:
        return max(14, round(20 * self.scale))

    def _schedule_icons(self) -> None:
        if self._icon_todo and self._icon_after is None:
            self._icon_after = self.root.after(30, self._icon_tick)

    def _icon_tick(self) -> None:
        """Carrega poucas imagens por vez, para a lista nunca travar mesmo com centenas de mods."""
        self._icon_after = None
        for _ in range(3):
            if not self._icon_todo:
                break
            path, source = self._icon_todo.pop(0)
            img = None
            try:
                img = self._load_icon(path, source)
            except Exception:  # noqa: BLE001  (imagem ruim: o mod fica sem ícone)
                img = None
            self._icons[path] = img
            iid = self._icon_iids.get(path)
            if img is not None and iid is not None and self.mod_tree.exists(iid):
                self.mod_tree.item(iid, image=img)
        self._schedule_icons()

    def _load_icon(self, path: Path, source: str):
        f = pick_icon_file(path, strict=(source == "avulso"))
        if f is None:
            return None
        px = self._icon_px()
        try:
            from PIL import Image, ImageTk  # opcional: com ele funcionam também JPG e imagens grandes

            im = Image.open(f).convert("RGBA")
            im.thumbnail((px, px))
            return ImageTk.PhotoImage(im)
        except ImportError:
            pass
        if f.suffix.lower() not in (".png", ".gif"):
            return None  # sem o Pillow o Tk só lê PNG e GIF
        img = tk.PhotoImage(file=str(f))
        k = icon_factor(img.width(), img.height(), px)
        return img.subsample(k) if k > 1 else img

    # ---------------------------------------------------------------- gráfico de velocidade
    def _redraw_spark(self) -> None:
        c = self.spark
        c.delete("all")
        w, h = int(c["width"]), int(c["height"])
        coords = sparkline_coords(self.rate.points, w, h)
        if coords:
            c.create_line(*coords, fill=ACCENT, width=2, smooth=True)

    def _spark_tip(self) -> str:
        if len(self.rate.points) < 2:
            return i18n.tr("Velocidade da tradução (textos por minuto). Aparece depois de alguns segundos.")
        return (i18n.tr("Velocidade da tradução (textos por minuto).") + "\n" + i18n.tr("Agora: ")
                + f"{self.rate.current:.0f}" + i18n.tr(" · Pico: ") + f"{self.rate.peak:.0f}")

    # ---------------------------------------------------------------- passo a passo e dicas
    def _tut_target(self, key: str):
        """Parte da janela que o tutorial destaca; None se ela não está visível (o passo é pulado)."""
        if key == "mods":
            if self.sidebar.winfo_ismapped():
                return self.cards.get("mods")
            return self.btn_drawer if self.btn_drawer.winfo_ismapped() else None
        if key == "help":
            return self.btn_help
        if key == "tutorial":
            return self.btn_tutorial
        if key == "settings":
            return self.btn_settings
        w = self.cards.get(key) or self.tt.get(key)
        if w is None:
            return None
        if key == "mod_buttons" and not self.sidebar.winfo_ismapped():
            return None  # a lista de mods está escondida (janela estreita)
        try:
            return w if w.winfo_ismapped() else None
        except tk.TclError:
            return None

    def open_tutorial_menu(self, first_run: bool = False) -> None:
        """Janela de boas-vindas: tutorial básico, avançado ou nenhum."""
        for other in (self.welcome, self.tour):
            if other is not None:
                try:
                    other.win.lift()
                except tk.TclError:
                    pass
                return
        self.welcome = Welcome(self, first_run)

    def start_tutorial(self, kind: str) -> None:
        if self.tour is not None:
            self.tour.close()
        self.tour = Tour(self, "advanced" if kind == "advanced" else "basic")

    def open_tour(self, first_run: bool = False) -> None:  # nome antigo
        self.open_tutorial_menu(first_run)

    def _auto_tip_text(self, w) -> str:
        """Dica (já no idioma do programa) para um botão/caixa de marcar; "" se não houver."""
        own = getattr(w, "_tip_text", None)  # dica ligada direto ao widget (setas, idiomas do mod)
        if own:
            return i18n.tr(own)
        try:
            text = str(w.cget("text"))
            ctx = getattr(w.winfo_toplevel(), "_tip_ctx", "")
        except tk.TclError:
            return ""
        cands = [getattr(w, "_i18n_text", None), text]  # o texto em português, mesmo com o programa em outro idioma
        tip = find_tip(ctx, cands, i18n.tr)
        if not tip:  # frases longas do programa ("Traduzir este mod"…) ficam na tabela antiga
            tip = next((t for k, t in TIPS_BY_TEXT if any(c and k in c for c in cands)), "")
        return i18n.tr(tip) if tip else ""

    def _attach_tips(self) -> None:
        """Dica ao passar o mouse nos botões e campos principais (texto do widget ou nome do atributo)."""
        def walk(w):
            yield w
            for c in w.winfo_children():
                yield from walk(c)

        def tip_for(key: str) -> str:
            return next((t for k, t in TIPS_BY_TEXT if k == key), "")

        for w in walk(self.root):
            try:
                text = str(w.cget("text")) if "text" in w.keys() else ""
            except tk.TclError:
                continue
            if not text or isinstance(w, (tk.Toplevel,)):
                continue
            for key, tip in TIPS_BY_TEXT:
                if key in text:
                    Tip(w, lambda t=tip: i18n.tr(t))
                    break
        for widget, key in ((self.src_box, "Idioma do mod:"), (self.dst_box, "Traduzir para:"),
                            (self.prov_box, "Serviço:"), (self.key_entry, "Chave:"), (self.url_entry, "Servidor:"),
                            (self.speed_scale, "Velocidade:")):
            tip = tip_for(key)
            if tip:
                Tip(widget, lambda t=tip: i18n.tr(t))

    def _schedule_refill(self) -> None:
        """Refaz a lista (filtro/ordem por progresso) quando chegam dados novos, no máximo 3 vezes por segundo."""
        if self._refill_after is None:
            self._refill_after = self.root.after(300, self._do_refill)

    def _do_refill(self) -> None:
        self._refill_after = None
        self.fill_mod_tree()

    def _hover_mod(self, event) -> None:
        iid = self.mod_tree.identify_row(event.y)
        self._show_mod_path(int(iid) if iid else None)

    def _show_mod_path(self, i: int | None = None) -> None:
        """Mostra o caminho completo do mod sob o mouse (ou do selecionado): útil quando há dois com o mesmo nome."""
        if i is None:
            sel = self.mod_tree.selection()
            i = int(sel[0]) if len(sel) == 1 else None
        self.mod_path_var.set(str(self.entries[i].path) if i is not None and i < len(self.entries) else "")

    def on_mod_select(self, event=None) -> None:
        """Um mod escolhido abre; vários escolhidos (Ctrl+clique) viram uma fila."""
        self._show_mod_path()
        if self._sel_after:
            self.root.after_cancel(self._sel_after)
        self._sel_after = self.root.after(300, self._apply_mod_selection)

    def _apply_mod_selection(self) -> None:
        self._sel_after = None
        sel = self.mod_tree.selection()
        n = len(sel)
        if self._narrow and self._drawer_open and n == 1:
            self.toggle_drawer()  # escolheu um mod: a gaveta some e o mod aparece
        self.btn_many.configure(text=i18n.tr("▶▶  Traduzir selecionados") + (f" ({n})" if n > 1 else "") + "  (Ctrl+Shift+T)")
        if n == 1 and not self._busy():
            entry = self.entries[int(sel[0])]
            if self.session.mod_path != entry.path:
                self.load_mod(entry.path)

    def pick_file(self) -> None:
        path = filedialog.askopenfilename(title="Escolha o mod", filetypes=[("Mods do Kenshi", "*.mod"), ("Todos", "*.*")])
        if not path:
            return
        p = Path(path)
        if not any(e.path == p for e in self.entries):
            self.entries.append(ModEntry(p.name, p, "avulso", p.stat().st_size))
            self.fill_mod_tree()
            threading.Thread(target=self._load_mod_info, args=(self.mod_gen, list(self.entries)), daemon=True).start()
        self.load_mod(p)

    def open_mod_folder(self) -> None:
        """Abre no Explorer a pasta onde o mod selecionado está (kenshi/mods/<mod> ou a pasta da Workshop)."""
        sel = self.mod_tree.selection()
        path = self.entries[int(sel[0])].path if sel and self.entries else self.session.mod_path
        if path is None:
            messagebox.showinfo("Pasta do mod", "Selecione um mod na lista primeiro.")
            return
        path = Path(path)
        folder = path if path.is_dir() else path.parent
        if not folder.is_dir():
            messagebox.showerror("Pasta do mod", f"Não achei a pasta desse mod: {folder}")
            return
        try:
            if sys.platform == "win32" and path.is_file():
                subprocess.Popen(["explorer", "/select,", str(path)])  # abre a pasta já com o .mod destacado
            else:
                open_with_system(folder)
        except Exception:  # noqa: BLE001
            try:
                open_with_system(folder)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Pasta do mod", f"Não consegui abrir a pasta: {e}")

    def pick_kenshi(self) -> None:
        folder = filedialog.askdirectory(title="Pasta onde o Kenshi está instalado")
        if not folder:
            return
        if not self.session.set_kenshi_dir(folder):
            messagebox.showerror("Kenshi", "Essa pasta não parece ser a do Kenshi (falta a pasta 'data').")
            return
        self.refresh_mods()

    # ================================================================ abrir um mod
    def load_mod(self, path: Path, force: bool = False) -> None:
        if self._busy():
            return
        if not force and self.session.mod_path == path and self.session.project is not None:
            return
        self._sync_cfg()
        self._set_busy(True, stoppable=False)
        self.status_var.set(f"Lendo {path.name}…")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)

        def job() -> None:
            try:
                self.session.open_mod(path)
                counts = self.session.detect_project_languages()
                self.events.put(("opened", path, counts))
            except Exception as e:  # noqa: BLE001 - arquivo ruim vira mensagem, não travamento
                self.events.put(("open_err", path, f"{type(e).__name__}: {e}"))

        self.worker = threading.Thread(target=job, daemon=True)
        self.worker.start()

    def _show_counts(self, counts: dict[str, int], first: bool = False) -> None:
        """Linha de informação sobre os idiomas do mod. first=True só na abertura (mexe nas caixas de idiomas)."""
        proj = self.session.project
        assert proj is not None
        present = present_languages(counts)
        st = proj.stats()
        names = " · ".join(f"{lang_name(k, i18n.language())} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]) if k != "und")
        base = f"{st['total']} textos para traduzir"
        if len(present) > 1:
            self.info_var.set(f"{base}. ATENÇÃO: este mod tem mais de um idioma: {names}. "
                              "Deixei marcada a opção de vários idiomas.")
            self.info_label.configure(fg=WARN)
            if first:
                self.multi_var.set(True)
                for code, var in self.src_checks.items():
                    var.set(code in present)
        else:
            self.info_var.set(f"{base}. Idioma: {names or 'indefinido'}.")
            self.info_label.configure(fg=MUTED)
            if first and self.multi_var.get() and len(present) <= 1:
                self.multi_var.set(False)

    def _on_opened(self, path: Path, counts: dict[str, int]) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self._set_busy(False)
        proj = self.session.project
        assert proj is not None
        self.counts = counts
        self.mod_var.set(proj.mod_name)
        st = proj.stats()
        self._show_counts(counts, first=True)
        self.on_multi_toggle(initial=True)
        self.last_built = None
        self.selected = None
        self.refresh_table()
        self.status_var.set(f"{st['pendente']} textos pendentes. Clique em “Traduzir este mod”.")
        info = proj.update_info
        if info and info.get("mod_mudou") and (info["novos"] or info["mudaram"]):
            self.status_var.set(f"O mod foi atualizado: {info['novos']} novos, {info['mudaram']} mudaram. "
                                "Veja em Ferramentas… > O que mudou.")
        self.eta_var.set("")

    # ================================================================ tabela e editor
    def _filter_code(self) -> str:
        for code, label in FILTER_LABEL.items():
            if i18n.tr(label) == self.filter_var.get():
                return code
        return "todos"

    def _debounced_table(self) -> None:
        if self._query_after:
            self.root.after_cancel(self._query_after)
        self._query_after = self.root.after(250, self.refresh_table)

    def refresh_table(self) -> None:
        self._query_after = None
        keep = self.selected
        self.tree.delete(*self.tree.get_children())
        self.refresh_lang_filter()
        rows = self.session.visible_units(self._filter_code(), self.query_var.get(), self.lang_code_selected())
        for i, u in rows[:MAX_ROWS]:
            self.tree.insert("", "end", iid=str(i), tags=(u.status,), values=(
                i18n.tr(STATUS_LABEL[u.status]), lang_name(u.lang, i18n.language()) if u.lang else "",
                one_line(u.source), one_line(u.translation)))
        proj = self.session.project
        if proj is not None:
            st = proj.stats()
            more = f" | mostrando {MAX_ROWS} de {len(rows)} (use o filtro ou a busca)" if len(rows) > MAX_ROWS else ""
            self.stats_var.set(
                f"{st['total']} textos | {st['pendente']} pendentes | {st['automatica']} automáticos | "
                f"{st['atencao']} p/ conferir | {st['revisada']} revisados | {proj.progress():.0%} resolvido"
                + self._doubtful_text() + more)
        if keep is not None and self.tree.exists(str(keep)):
            self.tree.selection_set(str(keep))
            self.tree.see(str(keep))

    def on_select(self, event=None) -> None:
        sel = self.tree.selection()
        if not sel or self.session.project is None:
            return
        self.selected = int(sel[0])
        u = self.session.project.units[self.selected]
        self.src_text.configure(state="normal")
        self.src_text.delete("1.0", "end")
        self.src_text.insert("1.0", u.source)
        self.src_text.configure(state="disabled")
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", u.translation)
        ctx = [u.record_name if u.field == "" else f"{u.record_name} / {u.field}"]
        ctx += [f"{k}: {v}" for k, v in u.context.items() if v]
        if u.note:
            ctx.append(f"nota: {u.note}")
        self.ctx_var.set(" | ".join(ctx))
        self.validate_editor()

    def validate_editor(self) -> None:
        if self.selected is None or self.session.project is None:
            return
        u = self.session.project.units[self.selected]
        ok, msg = self.session.check_translation(u, self.dst_text.get("1.0", "end-1c"))
        self.check_var.set(("✔ " if ok else "✖ ") + msg)
        self.check_label.configure(fg=OKFG if ok else RED)
        self.highlight_markers(u.source, self.dst_text.get("1.0", "end-1c"))

    def copy_source(self) -> None:
        if self.selected is None or self.session.project is None:
            return
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", self.session.project.units[self.selected].source)
        self.validate_editor()

    def apply_edit(self) -> None:
        if self.selected is None or self.session.project is None:
            return
        if self._busy():
            messagebox.showinfo("Aguarde", "Espere a tarefa terminar ou clique em Parar.")
            return
        try:
            self.session.edit(self.selected, self.dst_text.get("1.0", "end-1c"))
        except ValueError as e:
            messagebox.showwarning("Marcadores do jogo", str(e))
            return
        current = str(self.selected)
        children = list(self.tree.get_children())
        nxt = children[children.index(current) + 1] if current in children and children.index(current) + 1 < len(children) else None
        self.refresh_table()
        if nxt is not None and self.tree.exists(nxt):
            self.tree.selection_set(nxt)
            self.tree.see(nxt)

    # ================================================================ tarefas em segundo plano
    def _busy(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def _set_busy(self, busy: bool, stoppable: bool = True) -> None:
        state = "disabled" if busy else "normal"
        for b in (self.btn_translate, self.btn_many, self.btn_redo, self.btn_second, self.btn_build, self.btn_install, self.btn_restore):
            b.configure(state=state)
        self.btn_stop.configure(state="normal" if busy and stoppable else "disabled")
        self._stoppable = busy and stoppable
        if not busy:
            self._live_provider = None
            self.svc_var.set("")
            self._clear_service_lights()

    def _start_timer(self) -> None:
        self._t0, self._d0 = None, 0

    def _eta(self, done: int, total: int) -> str:
        now = time.time()
        if self._t0 is None:
            self._t0, self._d0 = now, done
            return ""
        dt, dd = now - self._t0, done - self._d0
        if dt < 3 or dd <= 0:
            return ""
        rate = dd / dt
        return f"{rate * 60:.0f} textos/min · faltam ≈ {fmt_duration((total - done) / rate)}"

    def test_provider(self) -> None:
        try:
            self._sync_cfg()
            provider = self.session.make_provider()
        except (ProviderError, ValueError) as e:
            messagebox.showerror("Serviço", str(e))
            return
        self.status_var.set("Testando o serviço…")

        def job() -> None:
            try:
                self.events.put(("test_ok", provider.test()))
            except Exception as e:  # noqa: BLE001
                self.events.put(("test_err", str(e)))

        threading.Thread(target=job, daemon=True).start()

    def _prepare_translation(self, retranslate: bool):
        try:
            self._sync_cfg()
            provider = self.session.make_provider()
        except (ProviderError, ValueError) as e:
            messagebox.showerror("Serviço", str(e))
            return None
        if not self._glossary_checkpoint(gate=True):
            return None
        if retranslate and not messagebox.askyesno(
            "Refazer", "Refazer as traduções automáticas e as marcadas para conferir?\n"
                       "O que você já revisou NÃO é alterado."):
            return None
        if self.cfg.multi_source and not self.cfg.source_langs:
            messagebox.showinfo("Idiomas", "Marque pelo menos um idioma que o mod tem, ou desmarque a opção de vários idiomas.")
            return None
        self.session.reload_glossary()
        self.cancel.clear()
        self._start_timer()
        self.rate.reset()
        self._redraw_spark()
        self._set_busy(True)
        self.progress.configure(mode="determinate", value=0, maximum=100)
        self.status_var.set("Começando…")
        self.eta_var.set(f"{self.cfg.workers} parte(s) ao mesmo tempo")
        self.notice_var.set("")
        self._live_provider = provider if hasattr(provider, "status") else None
        return provider

    def start_translate(self, retranslate: bool) -> None:
        if self.session.project is None:
            messagebox.showinfo("Kenshi Quick Translator", "Escolha um mod na lista primeiro.")
            return
        if self._busy():
            return
        provider = self._prepare_translation(retranslate)
        if provider is None:
            return
        if retranslate and self.session.mod_path is not None:
            try:
                self.session.project.save()
                self.session.backup_project(self.session.mod_path)
            except Exception:  # noqa: BLE001
                pass

        def job() -> None:
            try:
                report = self.session.translate(
                    provider,
                    progress=lambda d, t, m: self.events.put(("progress", d, t, m)),
                    cancel=self.cancel, retranslate=retranslate,
                )
                self.events.put(("done", report))
            except ProviderBroken as e:
                self.events.put(("broken", str(e)))
            except Exception as e:  # noqa: BLE001
                self.events.put(("error", f"{type(e).__name__}: {e}"))

        self.worker = threading.Thread(target=job, daemon=True)
        self.worker.start()

    def start_many(self) -> None:
        sel = self.mod_tree.selection()
        if not sel:
            messagebox.showinfo("Kenshi Quick Translator", "Escolha um ou mais mods na lista (Ctrl+clique para vários).")
            return
        if self._busy():
            return
        paths = [self.entries[int(i)].path for i in sel]
        self._many_iids = list(sel)  # linha da lista de cada mod da fila (para mostrar o andamento dele)
        if len(paths) > 1 and not messagebox.askyesno(
            "Traduzir em fila",
            f"Traduzir {len(paths)} mods, um depois do outro?\n\n"
            "Para cada um será gerado o mod de tradução"
            + (" e instalado no jogo" if self.install_var.get() else "") + "."):
            return
        provider = self._prepare_translation(False)
        if provider is None:
            return
        install = bool(self.install_var.get())

        def job() -> None:
            try:
                results = self.session.translate_many(
                    paths, provider,
                    progress=lambda i, n, name, d, t, m: self.events.put(("many_progress", i, n, name, d, t, m)),
                    cancel=self.cancel, install=install,
                )
                self.events.put(("many_done", results))
            except Exception as e:  # noqa: BLE001
                self.events.put(("error", f"{type(e).__name__}: {e}"))

        self.worker = threading.Thread(target=job, daemon=True)
        self.worker.start()

    def stop(self) -> None:
        self.cancel.set()
        self.status_var.set("Parando… o que já foi traduzido fica salvo.")

    def _poll(self) -> None:
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "progress":
                    _, done, total, msg = ev
                    self.progress.configure(maximum=max(total, 1), value=done)
                    self.status_var.set(f"{msg}: {done}/{total}")
                    if self.rate.add(time.time(), done):
                        self._redraw_spark()
                    eta = self._eta(done, total)
                    if eta:
                        self.eta_var.set(eta)
                    if time.time() - self.last_refresh > 1.5:
                        self.last_refresh = time.time()
                        self.refresh_table()
                elif kind == "notice":
                    self.notice_var.set("⚠ " + ev[1])
                elif kind == "many_progress":
                    _, i, n, name, done, total, msg = ev
                    if getattr(self, "_many_i", None) != i:
                        self._many_i = i
                        self._start_timer()
                    self.progress.configure(maximum=max(total, 1), value=done)
                    self._queue_live(i, done, total)
                    self.status_var.set(f"Mod {i + 1} de {n}: {name}  ({msg} {done}/{total})")
                    if self.rate.add(time.time(), done):
                        self._redraw_spark()
                    eta = self._eta(done, total)
                    if eta:
                        self.eta_var.set(eta)
                elif kind == "done":
                    self._finish(ev[1])
                elif kind == "many_done":
                    self._finish_many(ev[1])
                elif kind == "opened":
                    self._on_opened(ev[1], ev[2])
                elif kind == "open_err":
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=0)
                    self._set_busy(False)
                    self.session.mod_path = None
                    self.status_var.set("Não consegui ler esse mod.")
                    messagebox.showerror("Não consegui ler o mod", f"{ev[1].name}\n\n{ev[2]}")
                elif kind == "mod_info":
                    _, gen, i, label, prog = ev
                    if gen == self.mod_gen:
                        self.mod_counts[i] = label
                        label = self._mod_lang_text(label)
                        self.labels[i] = (label, "" if prog is None else f"{prog:.0%}")
                        if self.mod_tree.exists(str(i)):
                            text = "" if prog is None else f"{prog:.0%}"
                            self.mod_tree.set(str(i), "idioma", label)
                            self.mod_tree.set(str(i), "prog", text)
                            tags = ("done",) if text == "100%" else ("part",) if text and text != "0%" else ()
                            self.mod_tree.item(str(i), tags=tags)
                        if (self._code_from(MODFILTER_LABEL, self.modfilter_var, "todos") in ("sem", "incompleto", "completo")
                                or self._code_from(MODSORT_LABEL, self.modsort_var, "padrao") in ("menos", "mais")):
                            self._schedule_refill()
                elif kind == "broken":
                    self._set_busy(False)
                    self.refresh_table()
                    self.status_var.set("Serviço instável: parei.")
                    self._alert(bad=True)
                    self.broken_dialog(ev[1])
                elif kind == "error":
                    self._set_busy(False)
                    self.refresh_table()
                    self.status_var.set("Erro.")
                    messagebox.showerror("Erro inesperado", ev[1])
                elif kind == "test_ok":
                    self.status_var.set("Serviço ok.")
                    messagebox.showinfo("Serviço", f"Funcionou. Teste: “Hello, world!” → “{ev[1]}”")
                elif kind == "test_err":
                    self.status_var.set("O serviço não respondeu.")
                    messagebox.showerror("Serviço", friendly_error(ev[1]))
        except queue.Empty:
            pass
        self._show_services()
        self.root.after(100, self._poll)

    def _clear_service_lights(self) -> None:
        for w in self.svc_frame.winfo_children():
            w.destroy()
        self._svc_widgets.clear()
        self._svc_info.clear()

    def _show_services(self) -> None:
        """Luzes ao vivo: verde = ativo, amarelo = fora por pouco tempo, vermelho = falhou várias vezes seguidas.
        O motivo e o tempo aparecem ao passar o mouse sobre a luz."""
        prov = self._live_provider
        if prov is None:
            return
        now = time.time()
        if now - getattr(self, "_svc_at", 0) < 1.0:
            return
        self._svc_at = now
        if hasattr(prov, "status_detail"):
            rows = prov.status_detail()
        else:
            rows = [{"key": k, "name": n, "wait": w, "strikes": 0, "why": ""} for k, n, w in prov.status()]
        keys = [r["key"] for r in rows]
        if keys != list(self._svc_widgets):  # conjunto de serviços mudou: monta de novo
            self._clear_service_lights()
            ttk.Label(self.svc_frame, text=i18n.tr("Serviços: "), style="Muted.TLabel").pack(side="left")
            for r in rows:
                dot = tk.Label(self.svc_frame, text="●", bg=CARD, font=self.f_base)
                name = tk.Label(self.svc_frame, text="", bg=CARD, fg=MUTED, font=self.f_small)
                dot.pack(side="left", padx=(8, 0))
                name.pack(side="left", padx=(2, 4))
                self._svc_widgets[r["key"]] = (dot, name)
                for w in (dot, name):
                    Tip(w, lambda k=r["key"]: self._svc_info.get(k, ""))
        for r in rows:
            dot, name = self._svc_widgets[r["key"]]
            wait = r["wait"]
            if wait <= 0:
                color, tip = LIGHT_OK, i18n.tr("Ativo")
            else:
                color = LIGHT_BAD if (wait > 120 or r["strikes"] >= 3) else LIGHT_WAIT
                why = i18n.tr(r["why"]) if r["why"] else i18n.tr("falhou")
                tip = f"{why}. " + i18n.tr("Volta em ") + fmt_duration(wait)
                if r["strikes"] > 1:
                    tip += f"  ({r['strikes']} " + i18n.tr("falhas seguidas") + ")"
            dot.configure(fg=color)
            name.configure(text=r["name"])
            self._svc_info[r["key"]] = f"{r['name']}: {tip}"

    # ---------------------------------------------------------------- aviso ao terminar
    def _alert(self, bad: bool = False) -> None:
        """Som e piscar na barra de tarefas, para quem saiu do computador durante uma fila longa."""
        if not getattr(self.cfg, "notify_done", True):
            return
        try:
            import winsound  # só existe no Windows
            winsound.MessageBeep(winsound.MB_ICONHAND if bad else winsound.MB_ICONASTERISK)
        except Exception:  # noqa: BLE001
            try:
                self.root.bell()
            except tk.TclError:
                pass
        self._flash_taskbar()

    def _flash_taskbar(self) -> None:
        if sys.platform != "win32":
            return
        try:
            if self.root.focus_displayof() is not None:  # a janela já está em uso: não precisa piscar
                return
            import ctypes
            from ctypes import wintypes

            class FLASHWINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND), ("dwFlags", wintypes.DWORD),
                            ("uCount", wintypes.UINT), ("dwTimeout", wintypes.DWORD)]

            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            # 0x3 = botão e barra de título; 0xC = até a janela voltar ao primeiro plano
            info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 0x3 | 0xC, 0, 0)
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
        except Exception:  # noqa: BLE001
            pass

    def _doubtful_text(self) -> str:
        d = self.session.doubtful()
        return f" | ⚠ {d.total} duvidosos" if d.total else ""

    def _queue_live(self, i: int, done: int, total: int) -> None:
        """Mostra o andamento do mod da vez na própria lista (coluna de progresso); os já feitos ficam em 100%."""
        iids = getattr(self, "_many_iids", None) or []
        for k, iid in enumerate(iids):
            if not self.mod_tree.exists(iid):
                continue
            if k < i:
                text = "100%"
            elif k == i:
                text = f"{done * 100 // max(total, 1)}%"
            else:
                continue
            self.mod_tree.set(iid, "prog", text)

    def _finish(self, report) -> None:
        self._set_busy(False)
        self.refresh_table()
        self.progress.configure(value=self.progress["maximum"])
        parts = [f"{report.translated} traduzidos"]
        if report.from_memory:
            parts.append(f"{report.from_memory} da memória")
        if report.attention:
            parts.append(f"{report.attention} para conferir")
        if report.failed:
            parts.append(f"{report.failed} com falha")
        took = f" em {fmt_duration(report.seconds)}" if report.seconds >= 1 else ""
        self.status_var.set(("Interrompido. " if report.cancelled else "Pronto. ") + ", ".join(parts) + took + ".")
        self.eta_var.set("")
        self.refresh_mods(keep_selection=True)
        if not report.cancelled:
            self._alert(bad=bool(report.failed and not report.translated))
        resumo = (f"Traduzidos: {report.translated}\nDa memória: {report.from_memory}\n"
                  f"Para conferir: {report.attention}\nIgnorados: {report.ignored}\nCom falha: {report.failed}\n"
                  f"Tempo: {fmt_duration(report.seconds) if report.seconds >= 1 else 'menos de 1 s'}")
        try:
            from .consistency import glossary_usage
            used, missed = glossary_usage(self.session.project.units, self.session.glossary) if self.session.project else (0, 0)
            if used or missed:
                resumo += f"\n\nGlossário ({self.session.glossary_lang}): {used} textos usam o glossário"
                if missed:
                    resumo += f"; {missed} não usaram (veja Ferramentas > Conferir consistência)"
                resumo += "."
        except Exception:  # noqa: BLE001 - o resumo nunca pode falhar por causa disso
            pass
        if report.cancelled:
            resumo = "Parou antes de terminar (o que já foi traduzido está salvo).\n\n" + resumo
        if report.field_notes:
            resumo += "\n\n" + FIELD_NOTES_TITLE + "\n" + "\n".join(report.field_notes)
        if report.messages:
            resumo += "\n\nAvisos do serviço:\n" + "\n".join(dict.fromkeys(friendly_error(m) for m in report.messages))
            messagebox.showwarning("Resumo da tradução", resumo)
        else:
            messagebox.showinfo("Resumo da tradução", resumo)

    def _finish_many(self, results: list[ManyResult]) -> None:
        self._many_i = None
        self._set_busy(False)
        self.progress.configure(value=self.progress["maximum"])
        self.eta_var.set("")
        lines = []
        for r in results:
            if r.error:
                lines.append(f"✖ {r.name}: {r.error}")
            elif r.built is not None:
                extra = " (instalado)" if r.installed else ""
                warn = f"  ⚠ {len(r.built.problems)} problema(s)" if r.built.problems else ""
                lines.append(f"✔ {r.name}: {r.built.written} textos{extra}{warn}")
            else:
                lines.append(f"– {r.name}: nada para gerar")
        self.status_var.set(f"Fila terminada: {len(results)} mod(s).")
        self._alert(bad=bool(results) and all(r.error for r in results))
        self.refresh_mods(keep_selection=True)
        if self.session.mod_path is not None and not self._busy():
            self.load_mod(self.session.mod_path, force=True)
        folder = self.session.default_output_folder
        text = "\n".join(lines) + f"\n\nOs mods de tradução estão em:\n{folder}\n\nAbrir essa pasta?"
        if messagebox.askyesno("Fila terminada", text):
            try:
                open_with_system(folder)
            except Exception:  # noqa: BLE001
                pass

    # ================================================================ gerar / instalar
    def _ensure_project(self) -> bool:
        if self.session.project is None:
            messagebox.showinfo("Kenshi Quick Translator", "Escolha um mod na lista primeiro.")
            return False
        if self._busy():
            messagebox.showinfo("Aguarde", "Espere a tarefa terminar ou clique em Parar.")
            return False
        return True

    def build_mod(self) -> Path | None:
        if not self._ensure_project():
            return None
        proj = self.session.project
        assert proj is not None
        if not any(u.translation.strip() for u in proj.units):
            messagebox.showinfo("Nada para gerar", "Ainda não há nenhuma tradução. Clique em “Traduzir este mod”.")
            return None
        folder = self.session.default_output_folder
        folder.mkdir(parents=True, exist_ok=True)
        chosen = filedialog.askdirectory(title="Onde salvar o mod de tradução?", initialdir=str(folder))
        if not chosen:
            return None
        try:
            res = self.session.build(chosen)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Não consegui gerar o mod", str(e))
            return None
        self.last_built = res.path
        if res.problems:
            messagebox.showwarning("Gerado, mas confira",
                                   f"{res.path}\n\nProblemas encontrados:\n- " + "\n- ".join(res.problems[:12]))
        else:
            messagebox.showinfo("Mod gerado", f"{res.path}\n\n{res.written} textos traduzidos. Conferência do arquivo: ok.\n"
                                              "O mod original não foi alterado.")
        self.status_var.set(f"Gerado: {res.path.name}")
        return res.path

    def open_services(self) -> None:
        ServicesDialog(self.root, self.cfg)

    def open_settings(self) -> None:
        """Configurações gerais, em seções: aparência, avisos, tradução, instalação no jogo, dados e créditos."""
        win = tk.Toplevel(self.root)
        win._tip_ctx = "config"
        win.title(i18n.tr("Configurações gerais"))
        win.transient(self.root)
        win.configure(bg=BG)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w, h = min(840, sw - 60), min(800, sh - 90)
        win.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")
        win.minsize(min(640, w), min(420, h))

        # rodapé fixo com os botões; o resto rola se a tela for pequena
        foot = ttk.Frame(win, style="Card.TFrame", padding=(16, 10))
        foot.pack(side="bottom", fill="x")
        canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = ttk.Frame(canvas, style="Card.TFrame", padding=(22, 12))
        inner = canvas.create_window((0, 0), window=body, anchor="nw")
        body.columnconfigure(1, weight=1)
        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner, width=e.width))

        def _wheel(e) -> None:
            if body.winfo_reqheight() > canvas.winfo_height():
                canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

        win.bind("<MouseWheel>", _wheel)
        wrap = max(380, w - 140)
        row = [0]

        def heading(text: str) -> None:
            top = 0 if row[0] == 0 else 12
            tk.Label(body, text=i18n.tr(text), bg=CARD, fg=INK, font=self.f_bold).grid(
                row=row[0], column=0, columnspan=2, sticky="w", pady=(top, 2))
            ttk.Separator(body).grid(row=row[0] + 1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            row[0] += 2

        def tip(widget, text: str) -> None:
            """Explicação que aparece quando o mouse para em cima (nada de texto cinza embaixo)."""
            if text:
                Tip(widget, lambda t=text: i18n.tr(t))

        def check(text: str, var: tk.BooleanVar, hint: str = "") -> None:
            cb = ttk.Checkbutton(body, text=text, variable=var, style="Card.TCheckbutton")
            cb.grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(5, 0))
            row[0] += 1
            tip(cb, hint)

        def choice(label: str, var: tk.StringVar, values: list[str], width: int = 30, hint: str = "") -> None:
            lab = ttk.Label(body, text=label, style="Card.TLabel")
            lab.grid(row=row[0], column=0, sticky="w", pady=(6, 2))
            box = ttk.Combobox(body, textvariable=var, values=values, state="readonly", width=width)
            box.grid(row=row[0], column=1, sticky="w", padx=12, pady=(6, 2))
            row[0] += 1
            tip(lab, hint)
            tip(box, hint)

        # ---- Aparência
        heading("Aparência")
        names = list(i18n.LANG_NAMES.values())
        lang_var = tk.StringVar(value=i18n.LANG_NAMES.get(self.cfg.ui_lang, names[0]))
        choice("Idioma do programa:", lang_var, names,
               hint="A língua dos menus e botões. Não muda o idioma da tradução do mod.")
        from .galaxy import THEME_NAMES as FX_NAMES

        theme_keys = ["light", "dark", *EFFECT_THEMES, "auto"]
        theme_names = [i18n.tr("Claro"), i18n.tr("Escuro"), *(i18n.tr(FX_NAMES[k]) for k in EFFECT_THEMES),
                       i18n.tr("Seguir o Windows")]
        theme_var = tk.StringVar(value=theme_names[theme_keys.index(self.cfg.theme) if self.cfg.theme in theme_keys else 0])
        choice("Tema:", theme_var, theme_names, width=34,
               hint="Cores da janela. Os temas com nome têm uma faixa animada no topo, com degradê e luzes flutuando.")
        font_labels = [f"{i18n.tr(FONT_NAMES[p])} ({p}%)" for p in FONT_STEPS]
        cur_font = clamp_scale(self.cfg.font_scale)
        font_var = tk.StringVar(value=font_labels[FONT_STEPS.index(cur_font)] if cur_font in FONT_STEPS
                                else f"{cur_font}%")
        choice("Tamanho da letra:", font_var, font_labels, hint="Aumenta ou diminui as letras do programa.")

        # ---- Avisos
        heading("Avisos")
        notify = tk.BooleanVar(value=self.cfg.notify_switch)
        check("Avisar quando o programa trocar de serviço", notify,
              "Mostra um aviso quando um serviço de tradução falha e o programa passa para outro.")
        done_var = tk.BooleanVar(value=getattr(self.cfg, "notify_done", True))
        check("Tocar um som e piscar a janela quando a tradução terminar", done_var,
              "Útil em traduções demoradas: você pode usar outro programa e ser avisado quando acabar.")

        # ---- Tradução
        heading("Tradução")
        safetypes = tk.BooleanVar(value=self.cfg.safe_record_types)
        check("Modo seguro (recomendado)", safetypes,
              "Traduz só registros que têm texto de jogo (diálogos, itens, facções, personagens...). Animações, "
              "arquivos e efeitos ficam intactos, porque traduzir ali pode corromper o mod. Vale na próxima vez "
              "que o mod for aberto.")
        mode_keys = ["completo", "dependente"]
        mode_names = [i18n.tr(MODE_LABELS[k]) for k in mode_keys]
        mode_var = tk.StringVar(value=mode_names[mode_keys.index(self.cfg.translation_mode) if self.cfg.translation_mode in mode_keys else 0])
        mode_lab = ttk.Label(body, text="Tipo do mod traduzido:", style="Card.TLabel")
        mode_lab.grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(10, 2))
        row[0] += 1
        mode_box = ttk.Combobox(body, textvariable=mode_var, values=mode_names, state="readonly", width=82)
        mode_box.grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(0, 4))
        row[0] += 1
        plugin_note = ("Mods com plugins (RE_Kenshi, DLLs), como o Second Life of Kenshi: use Dependente. Esses mods procuram os "
                       "próprios arquivos pelo nome e pela pasta; uma cópia completa com outro nome faz o jogo cair.")
        for _w in (mode_lab, mode_box):
            Tip(_w, lambda: i18n.tr(MODE_NOTE) + "\n\n" + i18n.tr(plugin_note))

        # ---- Instalação no jogo
        heading("Instalação no jogo")
        images = tk.BooleanVar(value=self.cfg.copy_images)
        check("Copiar todos os arquivos do mod original ao instalar (modelos, texturas, .info, imagem)", images,
              "Modo Completo: copia a pasta inteira do original para a pasta do mod traduzido. "
              "Modo Dependente: copia só a imagem.")
        txtfiles = tk.BooleanVar(value=self.cfg.translate_text_files)
        check("Traduzir as dicas de carregamento do mod (tips.txt e outros .txt de frases)", txtfiles,
              "Vale para o modo Completo. As dicas aparecem na tela de carregamento do jogo.")
        tipsdep = tk.BooleanVar(value=self.cfg.translate_tips_dependent)
        check("Modo Dependente: levar também tips.txt e names*.txt", tipsdep,
              "Além do .mod e da imagem, coloca na pasta da tradução o tips.txt (traduzido) e as listas de nomes "
              "namesM/namesF/namesMF.txt (copiadas sem traduzir). A pasta do mod original nunca é tocada.")
        latin = tk.BooleanVar(value=self.cfg.latinize_names)
        check("Nomes em outro alfabeto: trocar por letras latinas (só quando detectar)", latin,
              "Se as listas namesM/namesF estiverem em russo, grego, japonês, coreano ou chinês e o idioma de destino "
              "usa letras latinas, os nomes são convertidos para letras latinas (o jogo não desenha outros alfabetos, "
              "e os nomes ficariam invisíveis). Nomes que já estão em letras latinas não são mexidos. Só vale para o modo Dependente.")
        localefiles = tk.BooleanVar(value=self.cfg.translate_locale_files)
        check("Mods com pasta locale: montar o idioma completo", localefiles,
              "Vale para o modo Completo. Corrige menu, falas e tela de início que ficam em inglês em mods como o Project Kathun, e traduz as "
              "frases do próprio mod. O original da pasta locale fica guardado como locale_off.")

        # ---- Dados e créditos
        heading("Dados e créditos")
        clean_btn = ttk.Button(body, text="Limpar dados…", command=lambda: self.open_cleanup(win))
        clean_btn.grid(row=row[0], column=0, sticky="w", pady=(4, 2))
        row[0] += 1
        tip(clean_btn, "Apaga projetos, memória de tradução e cópias do programa (você escolhe o quê). "
                       "Os mods não são alterados.")
        credits = tk.Label(body, text=i18n.tr(CREDITS_TEXT), bg=CARD, fg=MUTED, font=self.f_small, wraplength=wrap,
                           justify="left", cursor="hand2")
        credits.grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(14, 0))
        credits.bind("<Button-1>", lambda _e: webbrowser.open(CREDITS_URL))  # discreto: clicar abre a página do Kakrain

        def save() -> None:
            code = next((k for k, v in i18n.LANG_NAMES.items() if v == lang_var.get()), "pt")
            self.cfg.translation_mode = mode_keys[mode_names.index(mode_var.get())] if mode_var.get() in mode_names else "completo"
            changed = code != self.cfg.ui_lang
            self.cfg.ui_lang = code
            self.cfg.notify_switch = bool(notify.get())
            self.cfg.copy_images = bool(images.get())
            self.cfg.translate_text_files = bool(txtfiles.get())
            self.cfg.translate_tips_dependent = bool(tipsdep.get())
            self.cfg.latinize_names = bool(latin.get())
            self.cfg.translate_locale_files = bool(localefiles.get())
            self.cfg.safe_record_types = bool(safetypes.get())
            self.cfg.notify_done = bool(done_var.get())
            new_font = FONT_STEPS[font_labels.index(font_var.get())] if font_var.get() in font_labels else cur_font
            theme = theme_keys[theme_names.index(theme_var.get())] if theme_var.get() in theme_names else "light"
            theme_changed = theme != self.cfg.theme
            self.cfg.theme = theme
            self.cfg.save()
            if theme_changed:
                self.apply_theme(theme)
            self.set_font_scale(new_font)
            if changed:
                i18n.set_language(code)
                i18n.apply(self.root)
                self.relabel_languages()
            win.destroy()
            if changed:
                messagebox.showinfo("Configurações gerais", "Salvo. Alguns textos só mudam ao reiniciar o programa.")

        ttk.Button(foot, text="Cancelar", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(foot, text="Salvar", style="Accent.TButton", command=save).pack(side="right")
        i18n.apply(win)
        win.grab_set()

    def open_cleanup(self, parent: tk.Misc | None = None) -> None:
        """Janela "Limpar dados": escolhe o que apagar da pasta de dados do programa."""
        from . import cleanup

        if self._busy():
            messagebox.showinfo("Limpar dados", "Espere a tradução terminar (ou pare) antes de limpar.")
            return
        items = cleanup.scan(self.session.data_folder)
        win = tk.Toplevel(parent or self.root)
        win._tip_ctx = "limpar"
        win.title(i18n.tr("Limpar dados"))
        win.transient(parent or self.root)
        win.resizable(False, False)
        win.configure(bg=BG)
        body = ttk.Frame(win, style="Card.TFrame", padding=16)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(body, text=i18n.tr("Marque o que quer apagar. Só os dados deste programa são apagados: "
                                    "os mods, o mods.cfg e as cópias do original na pasta do Kenshi não são mexidos."),
                 bg=CARD, fg=MUTED, font=self.f_small, wraplength=460, justify="left").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        vars_: dict[str, tk.BooleanVar] = {}
        for r, it in enumerate(items, start=1):
            v = tk.BooleanVar(value=it.key in cleanup.DEFAULT_ON and it.files > 0)
            vars_[it.key] = v
            cb = ttk.Checkbutton(body, text=i18n.tr(it.label), variable=v, style="Card.TCheckbutton")
            cb.grid(row=r * 2 - 1, column=0, sticky="w", pady=(6, 0))
            if it.files == 0:
                cb.configure(state="disabled")
                v.set(False)
            info = f"{it.files} · {cleanup.human_size(it.size)}" if it.files else i18n.tr("nada para apagar")
            tk.Label(body, text=info, bg=CARD, fg=MUTED, font=self.f_small).grid(row=r * 2 - 1, column=1, sticky="e", padx=(12, 0))
            tk.Label(body, text=i18n.tr(it.note), bg=CARD, fg=MUTED, font=self.f_small, wraplength=440,
                     justify="left").grid(row=r * 2, column=0, columnspan=2, sticky="w", padx=(24, 0))

        def go() -> None:
            keys = [k for k, v in vars_.items() if v.get()]
            if not keys:
                messagebox.showinfo("Limpar dados", "Nada marcado.")
                return
            if not messagebox.askyesno("Limpar dados", "Apagar o que foi marcado? Isso não pode ser desfeito.\n"
                                       "Os mods em si não são alterados."):
                return
            res = self.session.clean_data(keys)
            if "config" in keys:
                fresh = Config()
                for f in dataclasses.fields(fresh):
                    setattr(self.cfg, f.name, getattr(fresh, f.name))
                self.cfg.save()
            win.destroy()
            self.refresh_mods(keep_selection=True)
            msg = f"{res.total} arquivo(s) apagado(s)."
            if "config" in keys:
                msg += "\n" + i18n.tr("Feche e abra o programa de novo para as configurações voltarem ao padrão.")
            if res.failed:
                msg += "\n\n" + i18n.tr("Não deu para apagar:") + "\n" + "\n".join(res.failed[:5])
            messagebox.showinfo("Limpar dados", msg)

        bb = ttk.Frame(body, style="Card.TFrame")
        bb.grid(row=99, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(bb, text="Cancelar", command=win.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bb, text="Apagar", style="Accent.TButton", command=go).pack(side="right")
        i18n.apply(win)
        win.grab_set()

    def reset_selected(self) -> None:
        sel = self.mod_tree.selection()
        if not sel:
            messagebox.showinfo("Zerar tradução", "Escolha na lista o mod que quer zerar.")
            return
        if self._busy():
            return
        names = [self.entries[int(i)].path for i in sel]
        if not messagebox.askyesno(
            "Zerar tradução",
            f"Apagar o progresso salvo de {len(names)} mod(s)? Eles voltam a 0%.\n"
            "Os mods em si não são alterados e fica uma cópia de segurança na pasta 'backup' dos projetos."):
            return
        n = sum(1 for name in names if self.session.reset_progress(name))
        self.refresh_mods(keep_selection=True)
        messagebox.showinfo("Zerar tradução", f"{n} mod(s) zerado(s)." if n else "Nenhum desses mods tinha progresso salvo.")

    def open_projects(self) -> None:
        folder = self.session.projects_folder
        folder.mkdir(parents=True, exist_ok=True)
        try:
            open_with_system(folder)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Pasta dos projetos", f"{folder}\n\n{e}")

    def copy_to_game(self) -> None:
        sel = self.mod_tree.selection()
        if not sel:
            messagebox.showinfo("Copiar mod", "Escolha na lista os mods do Workshop que quer copiar.")
            return
        entries = [self.entries[int(i)] for i in sel]
        if not messagebox.askyesno(
            "Copiar para a pasta do jogo",
            f"Copiar {len(entries)} mod(s) do Workshop para a pasta mods do Kenshi?\n"
            "O Workshop não é alterado; arquivos iguais na pasta do jogo serão substituídos."):
            return
        try:
            res = self.session.copy_to_game(entries)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Copiar mod", str(e))
            return
        messagebox.showinfo("Copiar mod", "\n".join(f"• {n}: {r}" for n, r in res))
        self.refresh_mods()

    def install_mod(self) -> None:
        if not self._ensure_project():
            return
        proj = self.session.project
        assert proj is not None
        if not any(u.translation.strip() for u in proj.units):
            messagebox.showinfo("Nada para instalar", "Ainda não há nenhuma tradução.")
            return
        dirs = self.session.locate_game()
        if dirs.kenshi is None:
            folder = filedialog.askdirectory(title="Pasta do Kenshi")
            if not folder or not self.session.set_kenshi_dir(folder):
                messagebox.showerror("Kenshi", "Não achei a pasta do Kenshi.")
                return
            dirs = self.session.locate_game()
        dependent = self.cfg.translation_mode == "dependente"
        if dependent:
            ask = (f"Isto vai instalar a tradução DEPENDENTE em {dirs.kenshi / 'mods'}: um arquivo pequeno com o idioma no nome, "
                   f"que precisa do original “{proj.mod_name}” instalado e ativo.\n• o original NÃO é alterado nem copiado\n"
                   "• a tradução é ativada em data/mods.cfg depois do original (é feito um backup do mods.cfg antes).\n\nContinuar?")
        else:
            ask = (f"Isto vai:\n• instalar o mod traduzido em {dirs.kenshi / 'mods'}, com o MESMO nome do original “{proj.mod_name}” "
                   f"(ele ocupa o lugar do original no jogo)\n• guardar o original como “{proj.mod_name}.original” "
                   f"nessa mesma pasta, se ainda não houver\n• garantir que “{proj.mod_name}” está ativo em data/mods.cfg "
                   "(é feito um backup do mods.cfg antes).\n\nContinuar?")
        if not messagebox.askyesno("Instalar no jogo", ask):
            return

        # roda em outra linha: copiar pastas grandes ou traduzir arquivos de idioma não pode travar a janela
        box = tk.Toplevel(self.root)
        box.title(i18n.tr("Instalando no jogo"))
        box.transient(self.root)
        box.resizable(False, False)
        box.configure(bg=BG)
        body = ttk.Frame(box, style="Card.TFrame", padding=20)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(body, text="Instalando no jogo… pode demorar em mods grandes. Não feche o programa.",
                  style="Card.TLabel").pack(anchor="w")
        bar = ttk.Progressbar(body, mode="indeterminate", length=380)
        bar.pack(fill="x", pady=(12, 0))
        bar.start(12)
        i18n.apply(box)
        box.protocol("WM_DELETE_WINDOW", lambda: None)
        box.grab_set()
        box.update_idletasks()
        sw, sh = box.winfo_screenwidth(), box.winfo_screenheight()
        box.geometry(f"+{(sw - box.winfo_reqwidth()) // 2}+{(sh - box.winfo_reqheight()) // 3}")
        out: dict = {}

        def work() -> None:
            try:
                res = self.session.build(self.session.default_output_folder)
                out["res"] = res
                if not res.problems:  # arquivo gerado com defeito: NÃO instala por cima do mod do jogo
                    out["dest"], out["changed"] = self.session.install(res.path)
            except Exception as e:  # noqa: BLE001
                out["err"] = e

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

        def poll() -> None:
            if worker.is_alive():
                self.root.after(150, poll)
                return
            bar.stop()
            box.destroy()
            self._install_done(out, proj)

        self.root.after(150, poll)

    def _install_done(self, out: dict, proj) -> None:
        if "err" in out:
            messagebox.showerror("Não consegui instalar", str(out["err"]))
            return
        res = out["res"]
        if res.problems:
            messagebox.showerror("Não instalei",
                                 "O mod gerado não passou na conferência, então nada foi instalado no jogo:\n- "
                                 + "\n- ".join(res.problems[:8]))
            return
        dest, changed = out["dest"], out["changed"]
        note = install_notice(self.session.last_install, proj.mod_name) if self.session.last_install else ""
        lat = getattr(self.session, "last_latinized", {})
        if lat:
            note = (note + "\n\n" if note else "") + i18n.tr("Nomes em outro alfabeto convertidos para letras latinas:") + " " + ", ".join(
                f"{k} ({v})" for k, v in lat.items())
        messagebox.showinfo("Instalado", f"{dest}\n\n" + ("mods.cfg atualizado." if changed else "mods.cfg já tinha o mod.")
                            + (f"\n\n{i18n.tr(note)}" if note else ""))
        self.status_var.set("Instalado. Abra o Kenshi para testar.")

    # ================================================================ glossário / PO
    def open_glossary(self) -> None:
        dlg = GlossaryDialog(self.root, self.session)
        dlg.win.bind("<Destroy>", lambda e: self.root.after(50, self.refresh_glossary_label) if e.widget is dlg.win else None)

    def export_po(self) -> None:
        if not self._ensure_project():
            return
        proj = self.session.project
        assert proj is not None
        path = filedialog.asksaveasfilename(defaultextension=".po", initialfile=f"{Path(proj.mod_name).stem}.po",
                                            filetypes=[("PO (Poedit)", "*.po")])
        if path:
            Path(path).write_text(proj.export_po(), encoding="utf-8")
            self.status_var.set(f"PO salvo: {Path(path).name}")

    def import_po(self) -> None:
        if not self._ensure_project():
            return
        proj = self.session.project
        assert proj is not None
        path = filedialog.askopenfilename(filetypes=[("PO (Poedit)", "*.po"), ("Todos", "*.*")])
        if not path:
            return
        n = proj.import_po(Path(path).read_text(encoding="utf-8"))
        proj.save()
        self.refresh_table()
        self.status_var.set(f"{n} traduções importadas (marcadas como revisadas).")

    # ================================================================ fechar
    def on_close(self) -> None:
        self.cancel.set()
        self.mod_gen += 1
        self._save_ui_state()  # antes de _sync_cfg, que grava o arquivo de configuração
        try:
            self._sync_cfg()
        except Exception:  # noqa: BLE001
            pass
        self.session.close()
        self.root.destroy()


class GlossaryDialog:
    """Editor do glossário: termos que saem sempre iguais ou que nunca devem ser traduzidos."""

    KEEP = "(manter como está)"

    def __init__(self, parent: tk.Tk, session: Session) -> None:
        self.session = session
        self.lang_name = LANGUAGES.get(session.glossary_lang, session.glossary_lang)
        # Português: cria o arquivo a partir do padrão para editar. Outros idiomas: o arquivo nasce quando salvar
        # (assim a oferta de presets do idioma não some só por abrir esta janela).
        self.path = session.ensure_glossary_file() if session.glossary_lang == "pt-BR" else session.glossary_file
        session.reload_glossary()
        self.glossary = session.glossary
        self.win = tk.Toplevel(parent)
        self.win._tip_ctx = "glossario"
        self.win.title(f"Glossário · {self.lang_name}")
        self.win.geometry("640x520")
        self.win.transient(parent)
        self.win.configure(bg=BG)

        tk.Label(self.win, bg=BG, fg=MUTED, justify="left", wraplength=600, text=(
            f"Glossário de {self.lang_name}: cada idioma de destino tem o seu, e este é o que vale quando você traduz para "
            f"{self.lang_name}. Termos que devem sair sempre do mesmo jeito. Deixe a tradução vazia para NÃO traduzir "
            "o termo (bom para nomes de lugares e facções).")).pack(anchor="w", padx=12, pady=(12, 6))

        mid = ttk.Frame(self.win)
        mid.pack(fill="both", expand=True, padx=12)
        self.tree = ttk.Treeview(mid, columns=("termo", "traducao"), show="headings", selectmode="browse")
        self.tree.heading("termo", text="Termo no mod")
        self.tree.heading("traducao", text="Como deve ficar")
        self.tree.column("termo", width=260)
        self.tree.column("traducao", width=300)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.Frame(self.win)
        form.pack(fill="x", padx=12, pady=8)
        self.term, self.tl = tk.StringVar(), tk.StringVar()
        ttk.Label(form, text="Termo:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.term, width=30).grid(row=0, column=1, padx=6, pady=2)
        ttk.Label(form, text="Tradução:").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.tl, width=30).grid(row=0, column=3, padx=6, pady=2)
        bar = ttk.Frame(self.win)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(bar, text="Adicionar / atualizar", command=self.add).pack(side="left")
        ttk.Button(bar, text="Remover", command=self.remove).pack(side="left", padx=6)
        ttk.Button(bar, text="Presets do Kenshi…", command=self.open_presets).pack(side="left", padx=6)
        ttk.Button(bar, text="Fechar", command=self.win.destroy).pack(side="right")
        self.fill()
        i18n.apply(self.win)

    def fill(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for term in sorted(self.glossary.terms, key=str.casefold):
            self.tree.insert("", "end", iid=term, values=(term, self.glossary.terms[term] or self.KEEP))

    def on_select(self, event=None) -> None:
        sel = self.tree.selection()
        if sel:
            self.term.set(sel[0])
            self.tl.set(self.glossary.terms.get(sel[0]) or "")

    def save(self) -> None:
        self.glossary.save(self.path)
        self.session.reload_glossary()

    def add(self) -> None:
        term = self.term.get().strip()
        if not term:
            return
        self.glossary.set(term, self.tl.get().strip() or None)
        self.save()
        self.fill()

    def remove(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        self.glossary.remove(sel[0])
        self.save()
        self.fill()
        self.term.set("")
        self.tl.set("")

    def open_presets(self) -> None:
        PresetsDialog(self.win, self.glossary, self.session.cfg.target_lang, on_done=self._presets_applied)

    def _presets_applied(self) -> None:
        self.save()
        self.fill()


class GlossaryOfferDialog:
    """Aparece quando o idioma de destino ainda não tem glossário: cada idioma tem o seu, para não misturar."""

    def __init__(self, parent, session: Session, offer: dict, gate: bool) -> None:
        self.session, self.offer, self.gate = session, offer, gate
        self.result = "cancel" if gate else "later"
        nome = LANGUAGES.get(offer["lang"], offer["lang"])
        self.win = tk.Toplevel(parent)
        self.win._tip_ctx = "glossario_oferta"
        self.win.title(f"{i18n.tr('Glossário')} · {nome}")
        self.win.transient(parent)
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        paras = [f"Você vai traduzir para {nome}. Cada idioma de destino tem o seu próprio glossário, "
                 "para não misturar nomes de idiomas diferentes."]
        others = session.other_glossaries()
        if others:
            lista = ", ".join(f"{LANGUAGES.get(c, c)} ({n} termos)" for c, n in others)
            paras.append(f"Seus outros glossários continuam guardados e voltam quando você escolher o idioma deles: {lista}.")
        if offer["official"]:
            paras.append(f"Para {nome} ainda não existe glossário. Posso criar um com os nomes oficiais do Kenshi em {nome}: "
                         f"cidades, facções e personagens com nome ({offer['total']} termos).")
            go = "Criar com os nomes oficiais"
        else:
            paras.append(f"Para {nome} ainda não existe glossário, e o Kenshi não tem tradução oficial nesse idioma. "
                         f"Posso criar um que mantém os nomes originais em inglês ({offer['total']} nomes de cidades, "
                         "facções e personagens). Isso é uma escolha do programa, não uma regra oficial.")
            go = "Criar mantendo os nomes originais"
        body = ttk.Frame(self.win)
        body.pack(fill="both", expand=True, padx=16, pady=(14, 4))
        for p in paras:
            tk.Label(body, bg=BG, fg=INK, justify="left", wraplength=500, text=i18n.tr(p)).pack(anchor="w", pady=(0, 8))
        tk.Label(body, bg=BG, fg=MUTED, justify="left", wraplength=500, text=i18n.tr(
            "Sem glossário, os nomes do jogo passam pelo tradutor como qualquer outra palavra e podem sair diferentes "
            "do Kenshi original.")).pack(anchor="w")
        bar = ttk.Frame(self.win)
        bar.pack(fill="x", padx=16, pady=14)
        ttk.Button(bar, text=go, style="Accent.TButton", command=self._go).pack(side="left")
        ttk.Button(bar, text="Escolher presets…", command=self._choose).pack(side="left", padx=8)
        if gate:
            ttk.Button(bar, text="Cancelar", command=self.win.destroy).pack(side="right")
            ttk.Button(bar, text="Traduzir sem glossário", command=self._none).pack(side="right", padx=8)
        else:
            ttk.Button(bar, text="Agora não", command=self.win.destroy).pack(side="right")
        i18n.apply(self.win)
        try:
            self.win.update_idletasks()
            self.win.grab_set()
            self.win.focus_set()
        except tk.TclError:
            pass

    def _go(self) -> None:
        self.session.accept_glossary_offer()
        self.result = "created"
        self.win.destroy()

    def _none(self) -> None:
        self.session.decline_glossary_offer()
        self.result = "none"
        self.win.destroy()

    def _choose(self) -> None:
        g = self.session.glossary
        done: list[int] = []

        def saved() -> None:
            g.save(self.session.glossary_file)
            self.session.reload_glossary()
            done.append(1)

        pd = PresetsDialog(self.win, g, self.offer["lang"], on_done=saved)
        self.win.wait_window(pd.win)
        if done and self.session.glossary.terms:
            self.result = "chosen"
            self.win.destroy()


class PresetsDialog:
    """Presets de glossário com os nomes oficiais do Kenshi (cidades, facções, personagens, armas, itens...)."""

    def __init__(self, parent, glossary: Glossary, target_lang: str, on_done) -> None:
        self.glossary = glossary
        self.on_done = on_done
        self.presets, self.official = presets_for(target_lang)
        self.win = tk.Toplevel(parent)
        self.win._tip_ctx = "presets"
        self.win.title("Presets do Kenshi")
        self.win.geometry("660x640")
        self.win.minsize(520, 420)
        self.win.transient(parent)
        self.win.configure(bg=BG)
        tk.Label(self.win, bg=BG, fg=MUTED, justify="left", wraplength=620, text=(
            f"Nomes como aparecem no Kenshi original em {LANGUAGES.get(target_lang, target_lang)}. Marque os que quer e clique em Adicionar. "
            "Termos que você já tem no glossário não são trocados, a não ser que marque a opção abaixo. "
            "Nome sem tradução aparece como \"(manter como está)\": o programa não o traduz.")).pack(anchor="w", padx=12, pady=(12, 6))
        self.vars: dict[str, tk.BooleanVar] = {}
        # Parte de baixo primeiro (botões sempre visíveis); a lista de presets rola no meio.
        bar = ttk.Frame(self.win)
        bar.pack(fill="x", padx=12, pady=12, side="bottom")
        ttk.Button(bar, text="Adicionar ao glossário", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Marcar todos", command=lambda: self._marcar(True)).pack(side="left", padx=6)
        ttk.Button(bar, text="Desmarcar", command=lambda: self._marcar(False)).pack(side="left")
        ttk.Button(bar, text="Fechar", command=self.win.destroy).pack(side="right")
        self.status = tk.StringVar(value="")
        tk.Label(self.win, bg=BG, fg=MUTED, textvariable=self.status, justify="left", wraplength=620).pack(
            anchor="w", padx=12, pady=(4, 0), side="bottom")
        self.overwrite = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.win, text="Trocar também os termos que já existem no meu glossário",
                        variable=self.overwrite).pack(anchor="w", padx=12, pady=(6, 0), side="bottom")
        if not self.official:
            tk.Label(self.win, bg=BG, fg=MUTED, wraplength=620, justify="left", text=(
                f"O Kenshi não tem tradução oficial em {target_lang}, então não há nomes oficiais para este idioma. "
                "Só existe o preset que mantém os nomes originais (em inglês). Isso é uma escolha, não uma regra oficial.")).pack(
                anchor="w", padx=12, pady=(6, 0), side="bottom")
        area = ttk.Frame(self.win)
        area.pack(fill="both", expand=True, padx=12)
        canvas = tk.Canvas(area, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        box = ttk.Frame(canvas)
        janela = canvas.create_window((0, 0), window=box, anchor="nw")
        box.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(janela, width=e.width))
        self.win.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        for p in self.presets:
            v = tk.BooleanVar(value=False)
            self.vars[p["id"]] = v
            ttk.Checkbutton(box, text=f"{p['nome']}  ({p['total']} termos)", variable=v).pack(anchor="w", pady=(6, 0))
            tk.Label(box, bg=BG, fg=MUTED, justify="left", wraplength=560, text=p["descricao"]).pack(anchor="w", padx=(24, 0))
        if not self.presets:
            tk.Label(box, bg=BG, fg=MUTED, text="Nenhum preset encontrado nesta instalação.").pack(anchor="w", pady=12)
        i18n.apply(self.win)

    def _marcar(self, valor: bool) -> None:
        for v in self.vars.values():
            v.set(valor)

    def apply(self) -> None:
        chosen = [pid for pid, v in self.vars.items() if v.get()]
        if not chosen:
            self.status.set("Marque pelo menos um preset.")
            return
        added = updated = skipped = 0
        for pid in chosen:
            a, u, s = self.glossary.merge(load_preset(pid), overwrite=self.overwrite.get())
            added, updated, skipped = added + a, updated + u, skipped + s
        self.on_done()
        self.status.set(f"Pronto. Novos: {added}. Trocados: {updated}. Que você já tinha e foram mantidos: {skipped}.")


class ServicesDialog:
    """Serviços do agregado: IAs no formato OpenAI (URL, chave e modelo editáveis), DeepL, Google Cloud, LibreTranslate."""

    def __init__(self, parent: tk.Tk, cfg) -> None:
        self.cfg = cfg
        self.win = tk.Toplevel(parent)
        self.win._tip_ctx = "servicos"
        self.win.title("Serviços do agregado")
        self.win.geometry("740x820")
        self.win.transient(parent)
        self.win.configure(bg=BG)
        self.result: list = []
        self.sel = -1
        top = ttk.Frame(self.win)
        top.pack(fill="x", padx=12, pady=(12, 4))
        self.use_free = tk.BooleanVar(value=cfg.use_free)
        self.spread = tk.BooleanVar(value=cfg.spread)
        ttk.Checkbutton(top, text="Incluir os serviços gratuitos (Google, Bing…) como reserva", variable=self.use_free,
                        command=self.save_flags).pack(anchor="w")
        ttk.Checkbutton(top, text="Dividir os lotes entre os serviços ao mesmo tempo", variable=self.spread,
                        command=self.save_flags).pack(anchor="w")
        tk.Label(self.win, bg=BG, fg=MUTED, justify="left", wraplength=660, text=(
            "Todos os serviços marcados trabalham juntos: se um bloquear ou falhar, o resto vai para outro. "
            "Os códigos do jogo (/TEAMUP/ etc.) são protegidos e conferidos em todos.")).pack(anchor="w", padx=12)
        mid = ttk.Frame(self.win)
        mid.pack(fill="x", padx=12, pady=6)
        self.tree = ttk.Treeview(mid, columns=("usar", "nome", "tipo", "modelo"), show="headings",
                                 selectmode="browse", height=6)
        for c, t, w in (("usar", "Usar", 50), ("nome", "Nome", 160), ("tipo", "Tipo", 230), ("modelo", "Modelo", 200)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        fr = ttk.Frame(self.win)
        fr.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Label(fr, text="Gratuitos (reserva): duplo clique marca ou desmarca; ▲▼ muda a ordem").pack(anchor="w")
        rf = ttk.Frame(fr)
        rf.pack(fill="x")
        self.free_tree = ttk.Treeview(rf, columns=("usar", "nome"), show="headings", selectmode="browse", height=5)
        self.free_tree.heading("usar", text="Usar")
        self.free_tree.heading("nome", text="Serviço gratuito")
        self.free_tree.column("usar", width=50)
        self.free_tree.column("nome", width=250)
        self.free_tree.pack(side="left")
        fb = ttk.Frame(rf)
        fb.pack(side="left", padx=6)
        b_up = ttk.Button(fb, text="▲", width=3, command=lambda: self.free_move(-1))
        b_up.pack(pady=1)
        b_up._tip_text = TIP_FREE_UP
        b_down = ttk.Button(fb, text="▼", width=3, command=lambda: self.free_move(1))
        b_down.pack(pady=1)
        b_down._tip_text = TIP_FREE_DOWN
        self.free_tree.bind("<Double-1>", self.free_toggle)
        order = [k for k in cfg.free_order if k in FREE_CLASSES]
        self.free_state = [[k, True] for k in order] + [[k, False] for k in DEFAULT_ORDER if k not in order]
        self.fill_free()

        f = ttk.Frame(self.win)
        f.pack(fill="x", padx=12, pady=4)
        self.v = {k: tk.StringVar() for k in ("kind", "preset", "name", "base_url", "api_key", "model", "rpm", "project", "credentials")}
        self.enabled = tk.BooleanVar(value=True)
        self.rows: dict[str, tuple] = {}

        def row(key, label, widget, kinds):
            lab = ttk.Label(f, text=label)
            self.rows[key] = (lab, widget, kinds)

        kinds_all = tuple(KINDS)
        self.kind_box = ttk.Combobox(f, textvariable=self.v["kind"], state="readonly", width=44, values=list(KINDS.values()))
        self.kind_box.bind("<<ComboboxSelected>>", lambda e: self.show_fields())
        row("kind", "Tipo:", self.kind_box, kinds_all)
        self.preset_box = ttk.Combobox(f, textvariable=self.v["preset"], state="readonly", width=44,
                                       values=[p["name"] for p in PRESETS])
        self.preset_box.bind("<<ComboboxSelected>>", self.on_preset)
        row("preset", "Modelo pronto:", self.preset_box, ("openai",))
        row("name", "Nome:", ttk.Entry(f, textvariable=self.v["name"], width=47), kinds_all)
        row("base_url", "URL base:", ttk.Entry(f, textvariable=self.v["base_url"], width=47), ("openai", "libretranslate"))
        row("api_key", "Chave:", ttk.Entry(f, textvariable=self.v["api_key"], show="•", width=47),
            ("openai", "deepl", "google-cloud", "libretranslate"))
        row("model", "Modelo:", ttk.Entry(f, textvariable=self.v["model"], width=47), ("openai",))
        row("rpm", "Pedidos/min (0 = sem limite):", ttk.Entry(f, textvariable=self.v["rpm"], width=8), ("openai",))
        row("project", "ID do projeto:", ttk.Entry(f, textvariable=self.v["project"], width=47), ("google-cloud-v3",))
        row("credentials", "Arquivo JSON (vazio = usar gcloud):", ttk.Entry(f, textvariable=self.v["credentials"], width=47),
            ("google-cloud-v3",))
        self.note = tk.Label(self.win, bg=BG, fg=MUTED, justify="left", wraplength=660, anchor="w")
        self.note.pack(fill="x", padx=12)
        ttk.Checkbutton(self.win, text="Usar este serviço", variable=self.enabled).pack(anchor="w", padx=12, pady=(4, 0))
        bar = ttk.Frame(self.win)
        bar.pack(fill="x", padx=12, pady=8)
        ttk.Button(bar, text="Novo", command=self.new).pack(side="left")
        ttk.Button(bar, text="Salvar este", style="Accent.TButton", command=self.save_one).pack(side="left", padx=6)
        ttk.Button(bar, text="Testar este", command=self.test_one).pack(side="left")
        ttk.Button(bar, text="Testar todos", command=self.test_all).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Remover", command=self.remove).pack(side="left", padx=6)
        m_up = ttk.Button(bar, text="▲", width=3, command=lambda: self.move(-1))
        m_up.pack(side="left")
        m_up._tip_text = TIP_LIST_UP
        m_down = ttk.Button(bar, text="▼", width=3, command=lambda: self.move(1))
        m_down.pack(side="left", padx=2)
        m_down._tip_text = TIP_LIST_DOWN
        ttk.Button(bar, text="Fechar", command=self.win.destroy).pack(side="right")
        tk.Label(self.win, bg=BG, fg=MUTED, justify="left", wraplength=660, anchor="w", text=(
            "Mais de uma chave do mesmo serviço? Separe com ;  Os nomes de modelo e as URLs são sugestões tiradas das "
            "documentações e mudam com o tempo: confira na página do serviço. Google Cloud v3 não aceita chave de API.")
        ).pack(fill="x", padx=12)
        self.new()
        self.fill()
        i18n.apply(self.win)

    # -- dados
    @property
    def items(self) -> list[dict]:
        return self.cfg.services

    def fill_free(self) -> None:
        self.free_tree.delete(*self.free_tree.get_children())
        for i, (k, on) in enumerate(self.free_state):
            self.free_tree.insert("", "end", iid=str(i), values=("✓" if on else "—", FREE_CLASSES[k].short))

    def free_save(self) -> None:
        self.cfg.free_order = [k for k, on in self.free_state if on]
        if not self.cfg.free_order and self.use_free.get():
            self.use_free.set(False)  # nenhum gratuito marcado = não incluir os gratuitos
        self.cfg.use_free = bool(self.use_free.get())
        self.cfg.save()

    def free_toggle(self, event=None) -> None:
        row = self.free_tree.identify_row(event.y) if event else ""
        if row:
            self.free_state[int(row)][1] = not self.free_state[int(row)][1]
            self.fill_free()
            self.free_save()

    def free_move(self, d: int) -> None:
        s = self.free_tree.selection()
        if not s:
            return
        i, j = int(s[0]), int(s[0]) + d
        if 0 <= j < len(self.free_state):
            self.free_state[i], self.free_state[j] = self.free_state[j], self.free_state[i]
            self.fill_free()
            self.free_tree.selection_set(str(j))
            self.free_save()

    def save_flags(self) -> None:
        self.cfg.use_free = bool(self.use_free.get())
        self.cfg.spread = bool(self.spread.get())
        self.cfg.save()

    def fill(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.items):
            self.tree.insert("", "end", iid=str(i), values=(
                "✓" if e.get("enabled", True) else "—", e.get("name", ""), KINDS.get(e.get("kind", ""), ""), e.get("model", "")))

    def kind_key(self) -> str:
        return next((k for k, v in KINDS.items() if v == self.v["kind"].get()), "openai")

    def show_fields(self) -> None:
        kind = self.kind_key()
        r = 0
        for key, (lab, widget, kinds) in self.rows.items():
            if kind in kinds:
                lab.grid(row=r, column=0, sticky="w", pady=2)
                widget.grid(row=r, column=1, sticky="w", padx=6, pady=2)
                r += 1
            else:
                lab.grid_remove()
                widget.grid_remove()
        notes = {
            "openai": "Formato OpenAI: POST {URL base}/chat/completions com a chave no cabeçalho Authorization.",
            "deepl": "Chave de API do DeepL (a que termina em :fx usa o servidor gratuito).",
            "google-cloud": "Cloud Translation v2 (Basic) com chave de API.",
            "google-cloud-v3": "v3 em lote. Login por arquivo JSON de conta de serviço (precisa: python -m pip install "
                               "cryptography) ou pelo gcloud já logado. Eu não testei este serviço.",
            "libretranslate": "URL do servidor LibreTranslate (próprio ou público) e, se exigir, a chave.",
        }
        self.note.configure(text=i18n.tr(notes.get(kind, "")))

    def on_preset(self, event=None) -> None:
        p = next((x for x in PRESETS if x["name"] == self.v["preset"].get()), None)
        if p:
            self.v["name"].set(p["name"] if p["name"] != "Outra IA compatível" else "Minha IA")
            self.v["base_url"].set(p["base_url"])
            self.v["model"].set(p["model"])
            self.note.configure(text=p["note"])

    def new(self) -> None:
        self.sel = -1
        for k, var in self.v.items():
            var.set("")
        self.v["kind"].set(KINDS["openai"])
        self.v["rpm"].set("30")
        self.enabled.set(True)
        self.show_fields()

    def on_select(self, event=None) -> None:
        s = self.tree.selection()
        if not s:
            return
        self.sel = int(s[0])
        e = self.items[self.sel]
        for k, var in self.v.items():
            var.set(str(e.get(k, "")))
        self.v["kind"].set(KINDS.get(e.get("kind", "openai"), KINDS["openai"]))
        self.enabled.set(bool(e.get("enabled", True)))
        self.show_fields()

    def collect(self) -> dict:
        kind = self.kind_key()
        e = {"kind": kind, "enabled": bool(self.enabled.get())}
        for k in ("name", "base_url", "api_key", "model", "project", "credentials"):
            e[k] = self.v[k].get().strip()
        try:
            e["rpm"] = max(0.0, float(self.v["rpm"].get().replace(",", ".") or 0))
        except ValueError:
            e["rpm"] = 30.0
        if not e["name"]:
            e["name"] = KINDS[kind]
        old = self.items[self.sel] if 0 <= self.sel < len(self.items) else {}
        e["id"] = old.get("id") or f"{kind}-{int(time.time() * 1000) % 10**9}"
        return e

    def save_one(self) -> None:
        e = self.collect()
        if 0 <= self.sel < len(self.items):
            self.items[self.sel] = e
        else:
            self.items.append(e)
            self.sel = len(self.items) - 1
        self.cfg.save()
        self.fill()
        self.tree.selection_set(str(self.sel))

    def remove(self) -> None:
        if 0 <= self.sel < len(self.items):
            del self.items[self.sel]
            self.cfg.save()
            self.fill()
            self.new()

    def move(self, d: int) -> None:
        j = self.sel + d
        if 0 <= self.sel < len(self.items) and 0 <= j < len(self.items):
            self.items[self.sel], self.items[j] = self.items[j], self.items[self.sel]
            self.sel = j
            self.cfg.save()
            self.fill()
            self.tree.selection_set(str(j))

    def test_one(self) -> None:
        try:
            provider = build_service(self.collect())
        except ProviderError as e:
            messagebox.showerror("Testar serviço", str(e))
            return
        self._run_test(provider)

    def test_all(self) -> None:
        self.save_flags()
        try:
            provider = build_aggregate(self.items, self.cfg.free_order, self.cfg.use_free, False)
        except ProviderError as e:
            messagebox.showerror("Testar serviços", str(e))
            return
        self._run_test(provider)

    def _run_test(self, provider) -> None:
        self.result = []

        def job() -> None:
            try:
                self.result = ["ok", provider.test()]
            except ProviderError as e:
                self.result = ["erro", str(e)]
            except Exception as e:  # noqa: BLE001 - qualquer falha vira mensagem, não trava a janela
                self.result = ["erro", f"{type(e).__name__}: {e}"]

        threading.Thread(target=job, daemon=True).start()
        self._wait_test()

    def _wait_test(self) -> None:
        if not self.result:
            self.win.after(200, self._wait_test)
            return
        kind, text = self.result
        (messagebox.showinfo if kind == "ok" else messagebox.showerror)(
            "Testar serviço", f"Funcionou. Resposta de teste: {text}" if kind == "ok" else f"Não funcionou:\n{text}")


def _definir_icone(root: tk.Tk) -> None:
    """Ícone da janela e da barra de tarefas (funciona no .exe e rodando pelo Python).

    No Windows o Tk escolhe um único tamanho do .ico e o estica (fica pixelado). Por isso
    pedimos ao próprio Windows o tamanho certo (pequeno e grande) com LoadImage/WM_SETICON.
    """
    pasta = Path(__file__).resolve().parent
    ico = pasta / "icone.ico"
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            user32.LoadImageW.restype = wintypes.HANDLE
            user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                          ctypes.c_int, ctypes.c_int, wintypes.UINT]
            user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            root.iconbitmap(default=str(ico))  # impede o Tk de usar a "pena" azul padrão

            def aplicar() -> None:
                try:
                    hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
                    try:
                        dpi = user32.GetDpiForWindow(hwnd) or 96
                    except Exception:  # noqa: BLE001  (Windows antigo)
                        dpi = 96
                    win11 = getattr(sys.getwindowsversion(), "build", 0) >= 22000
                    # Tamanho EXATO da barra de tarefas (24 px no Win11, 32 px no Win10, a 100%).
                    # Se o Windows precisar redimensionar, o ícone fica borrado.
                    grande = round((24 if win11 else 32) * dpi / 96)
                    pequeno = round(16 * dpi / 96)
                    icones = []
                    for tipo, tam in ((1, grande), (0, pequeno)):  # 1 = ICON_BIG, 0 = ICON_SMALL
                        h = user32.LoadImageW(None, str(ico), 1, tam, tam, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
                        if h:
                            user32.SendMessageW(hwnd, 0x0080, tipo, h)  # WM_SETICON
                            icones.append(h)
                    root._icones_win = icones  # mantém vivos
                except Exception:  # noqa: BLE001  (fica com o ícone do iconbitmap)
                    pass

            # O Tk reaplica o ícone dele quando a janela aparece; por isso aplicamos de novo depois.
            for ms in (50, 300, 1000):
                root.after(ms, aplicar)
        else:
            root.iconphoto(True, tk.PhotoImage(file=str(pasta / "icone.png")))
    except Exception:  # noqa: BLE001  (sem ícone o programa funciona igual)
        pass


def run() -> None:
    if sys.platform == "win32":
        try:  # evita janela borrada em telas com escala
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
        try:  # barra de tarefas usa o ícone do programa, não o do Python
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Canela.KenshiQuickTranslator")
        except Exception:  # noqa: BLE001
            pass
    root = tk.Tk()
    _definir_icone(root)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run()
