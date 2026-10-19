"""
Ações novas da janela (v0.6.0): restaurar o original, aviso do backup, desfazer, destaque de
marcadores, filtro por idioma de origem, segunda passada e janela de erro com botões de ação.

É um "mixin" da classe App (gui.py). A lógica fica em review.py / restore.py / session.py, que
têm testes; aqui só há janela, e ela NÃO pôde ser aberta no ambiente de desenvolvimento (sem Tkinter).
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import i18n
from .core import InstallInfo, ProviderBroken
from .langdetect import lang_name
from .providers import SPECS, friendly_error
from .review import marker_diff, marker_spans_source

ALL_LANGS = "Todos os idiomas"


def install_notice(info: InstallInfo, mod_name: str) -> str:
    """Texto (em português; passa por i18n.tr) sobre o que aconteceu com o original ao instalar."""
    if info.backup is None:
        return ""
    if info.backup_created:
        return (f"O ORIGINAL foi guardado em:\n{info.backup}\n"
                "Para desfazer a instalação use o botão “Restaurar o original”.")
    return (f"O original continua guardado em:\n{info.backup}\n"
            "(a cópia feita na primeira instalação não foi mexida).")


class ActionsMixin:
    # ------------------------------------------------------------ restaurar o original
    def restore_original_ui(self) -> None:
        if not self._ensure_project():
            return
        proj = self.session.project
        if not self.session.has_original_backup():
            messagebox.showinfo(
                "Restaurar o original",
                "Não achei uma cópia do original deste mod na pasta do jogo.\n"
                "Ela só existe se a tradução já foi instalada por este programa (modo completo).")
            return
        if not messagebox.askyesno(
                "Restaurar o original",
                f"Trocar o mod instalado “{proj.mod_name}” pelo ORIGINAL guardado?\n\n"
                "A tradução instalada não é apagada: fica ao lado com o final “.traduzido”."):
            return
        try:
            res = self.session.restore_original()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Restaurar o original", str(e))
            return
        extra = (f"\n\nA tradução que estava instalada ficou em:\n{res.kept_translation}"
                 if res.kept_translation else "")
        messagebox.showinfo("Restaurar o original", f"O original voltou:\n{res.mod_file}{extra}")
        self.status_var.set("Original restaurado.")

    # ------------------------------------------------------------ desfazer
    def undo_edit_ui(self) -> None:
        if self.session.project is None or self._busy():
            return
        idx = self.session.undo_edit()
        if idx is None:
            self.status_var.set("Nada para desfazer.")
            return
        self.selected = idx
        self.refresh_table()
        if self.tree.exists(str(idx)):
            self.tree.selection_set(str(idx))
            self.tree.see(str(idx))
        self.on_select()
        self.status_var.set("Edição desfeita.")

    # ------------------------------------------------------------ marcadores coloridos
    def setup_marker_tags(self) -> None:
        from . import gui as G  # cores da paleta atual (mudam com o tema)

        for w in (self.src_text, self.dst_text):
            w.tag_configure("mok", foreground=G.OKFG, font=self.f_bold)
            w.tag_configure("mbad", foreground=G.RED, underline=True, font=self.f_bold)

    def highlight_markers(self, source: str, translation: str) -> None:
        """Verde: marcador presente nos dois lados. Vermelho: faltando na tradução (marcado no
        original) ou sobrando nela. O texto do original é só leitura, então só mudamos a cor."""
        diff = marker_diff(source, translation)
        for w in (self.src_text, self.dst_text):
            w.tag_remove("mok", "1.0", "end")
            w.tag_remove("mbad", "1.0", "end")
        missing = list(diff.missing)
        for a, b in marker_spans_source(source):
            name = source[a:b]
            tag = "mok"
            if name in missing:
                missing.remove(name)
                tag = "mbad"
            self.src_text.tag_add(tag, f"1.0+{a}c", f"1.0+{b}c")
        for a, b, ok in diff.spans:
            self.dst_text.tag_add("mok" if ok else "mbad", f"1.0+{a}c", f"1.0+{b}c")

    # ------------------------------------------------------------ filtro por idioma de origem
    def lang_code_selected(self) -> str:
        sel = self.lang_var.get()
        if sel in ("", i18n.tr(ALL_LANGS)):
            return ""
        for code in self.session.source_language_counts():
            if lang_name(code, i18n.language()) == sel:
                return code
        return ""

    def refresh_lang_filter(self) -> None:
        """Mostra a caixa só quando o mod tem textos em mais de um idioma identificado."""
        counts = self.session.source_language_counts()
        names = [lang_name(c, i18n.language()) for c in sorted(counts, key=counts.get, reverse=True)]
        if len(counts) < 2:
            self.lang_box.pack_forget()
            self.lang_var.set(i18n.tr(ALL_LANGS))
            return
        self.lang_box.configure(values=[i18n.tr(ALL_LANGS)] + names)
        if self.lang_var.get() not in [i18n.tr(ALL_LANGS)] + names:
            self.lang_var.set(i18n.tr(ALL_LANGS))
        if not self.lang_box.winfo_ismapped():
            self.lang_box.pack(side="left", padx=(0, 6), after=self.filter_box)

    # ------------------------------------------------------------ segunda passada
    def second_pass_ui(self) -> None:
        if not self._ensure_project():
            return
        n = sum(1 for u in self.session.project.units if u.status == "atencao")
        if not n:
            messagebox.showinfo("Segunda passada", "Não há textos em “Conferir” neste mod.")
            return
        service = self._ask_service(n)
        if service is None:
            return
        try:
            self._sync_cfg()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Serviço", str(e))
            return
        self.cancel.clear()
        self._start_timer()
        self.rate.reset()
        self._redraw_spark()
        self._set_busy(True)
        self.progress.configure(mode="determinate", value=0, maximum=100)
        self.status_var.set("Segunda passada…")
        self.notice_var.set("")
        self._live_provider = None
        try:
            self.session.project.save()
            self.session.backup_project(self.session.mod_path)  # cópia de segurança antes de mexer
        except Exception:  # noqa: BLE001
            pass

        def job() -> None:
            try:
                report = self.session.second_pass(
                    service or None,
                    progress=lambda d, t, m: self.events.put(("progress", d, t, m)),
                    cancel=self.cancel)
                self.events.put(("done", report))
            except ProviderBroken as e:
                self.events.put(("broken", str(e)))
            except Exception as e:  # noqa: BLE001
                self.events.put(("error", f"{type(e).__name__}: {e}"))

        self.worker = threading.Thread(target=job, daemon=True)
        self.worker.start()

    def _ask_service(self, n: int) -> str | None:
        """Pergunta qual serviço usar na segunda passada. Devolve a chave ('' = o serviço atual) ou None."""
        win = tk.Toplevel(self.root)
        win.title(i18n.tr("Segunda passada"))
        win.transient(self.root)
        win.resizable(False, False)
        body = ttk.Frame(win, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, wraplength=420, justify="left", text=i18n.tr(
            "Refazer os textos em “Conferir” com outro serviço. O que sair melhor substitui; "
            "o que continuar com problema fica como estava. O que você revisou não é alterado.")
                  + f"  ({n})").pack(anchor="w")
        current = i18n.tr("O serviço atual (o mesmo da tradução)")
        options = [(current, "")] + [(s.label, s.key) for s in SPECS if s.key != "simulado"]
        var = tk.StringVar(value=options[0][0])
        ttk.Combobox(body, textvariable=var, state="readonly", width=56,
                     values=[o[0] for o in options]).pack(fill="x", pady=10)
        result: dict[str, str | None] = {"v": None}

        def ok() -> None:
            result["v"] = dict(options)[var.get()]
            win.destroy()

        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Button(row, text=i18n.tr("Começar"), command=ok).pack(side="right")
        ttk.Button(row, text=i18n.tr("Cancelar"), command=win.destroy).pack(side="right", padx=6)
        win.grab_set()
        self.root.wait_window(win)
        return result["v"]

    # ------------------------------------------------------------ erro com botões de ação
    def error_dialog(self, title: str, text: str, retry=None, switch=None) -> None:
        """Janela de erro com saídas práticas: tentar de novo (continua de onde parou) e trocar de serviço."""
        win = tk.Toplevel(self.root)
        win.title(i18n.tr(title))
        win.transient(self.root)
        win.resizable(False, False)
        body = ttk.Frame(win, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=text, wraplength=460, justify="left").pack(anchor="w")
        ttk.Label(body, wraplength=460, justify="left", style="Muted.TLabel",
                  text=i18n.tr("O que já foi traduzido está salvo.")).pack(anchor="w", pady=(8, 12))
        row = ttk.Frame(body)
        row.pack(fill="x")

        def run(fn):
            win.destroy()
            if fn:
                self.root.after(50, fn)

        ttk.Button(row, text=i18n.tr("Fechar"), command=win.destroy).pack(side="right")
        if switch:
            ttk.Button(row, text=i18n.tr("Trocar de serviço…"), command=lambda: run(switch)).pack(side="right", padx=6)
        if retry:
            ttk.Button(row, text=i18n.tr("Tentar de novo"), style="Accent.TButton",
                       command=lambda: run(retry)).pack(side="right")
        i18n.apply(win)
        win.grab_set()

    def broken_dialog(self, message: str) -> None:
        self.error_dialog("O serviço falhou", friendly_error(message),
                          retry=lambda: self.start_translate(False),
                          switch=self.focus_service_choice)

    def focus_service_choice(self) -> None:
        box = getattr(self, "prov_box", None)
        if box is not None:
            try:
                box.focus_set()
                box.event_generate("<Down>")
            except tk.TclError:
                pass
