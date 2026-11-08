"""
Janelas novas da v0.7.3: Ferramentas do mod, Modo simples e relatório de erro.

Mixin da classe App (gui.py). A lógica fica em suggest.py, fontcheck.py, errorreport.py e project.py
(com testes em tests/test_tools.py). Aqui só há janela: NÃO foi aberta no ambiente de desenvolvimento
(sem Tkinter), então o layout só foi conferido pelo compilador.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, fontcheck, i18n, suggest
from .errorreport import build_report, format_exc, install_crash_log, log_error, log_path
from .glossary import load_preset, presets_for


class ToolsMixin:
    last_error = ""

    # ------------------------------------------------------------ erro
    def _install_error_hook(self) -> None:
        """Guarda o último erro não tratado da janela, para o botão “Copiar relatório de erro”."""
        def hook(exc_type, exc, tb) -> None:
            self.last_error = format_exc(exc_type, exc, tb)
            log_error(self.last_error)
            try:
                self.status_var.set("Algo deu errado. Use Ferramentas > Copiar relatório de erro.")
            except Exception:  # noqa: BLE001
                pass
            try:
                if sys.stderr is not None:  # no .exe sem janela de texto não existe stderr
                    sys.stderr.write(self.last_error)
            except Exception:  # noqa: BLE001
                pass
        self.root.report_callback_exception = hook
        install_crash_log()

    def error_report_text(self) -> str:
        s = self.session
        p = s.project
        info = {
            "Mod": p.mod_name if p else "",
            "Idiomas": f"{s.cfg.source_lang} -> {s.cfg.target_lang}",
            "Serviço": getattr(s.cfg, "provider", ""),  # nunca inclui chaves de API
            "Textos": (f"{p.stats()}" if p else ""),
            "Status na tela": self.status_var.get(),
            "Aviso na tela": self.notice_var.get() if hasattr(self, "notice_var") else "",
        }
        info["Arquivo de log"] = str(log_path())
        return build_report(__version__, info, self.last_error)

    def copy_error_report(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.error_report_text())
        messagebox.showinfo("Relatório de erro", "Relatório copiado. Cole na conversa ou no GitHub.\nEle não contém suas chaves de API.")

    # ------------------------------------------------------------ ferramentas
    def open_tools(self) -> None:
        from . import gui as G  # cores do tema atual (variáveis do módulo)
        win = tk.Toplevel(self.root)
        win._tip_ctx = "ferramentas"
        win.title(i18n.tr("Ferramentas do mod"))
        win.geometry("720x560")
        win.minsize(520, 380)
        win.transient(self.root)
        win.configure(bg=G.BG)
        self._tools_win = win
        top = ttk.Frame(win)
        top.pack(fill="x", padx=10, pady=(10, 4))
        self._tools_btn_row = ttk.Frame(win)
        self._tools_btn_row.pack(fill="x", padx=10, pady=(0, 6), side="bottom")
        ttk.Button(top, text="Sugerir presets", command=self._tool_presets).pack(side="left")
        ttk.Button(top, text="Nomes novos do mod", command=self._tool_names).pack(side="left", padx=4)
        ttk.Button(top, text="Conferir caracteres", command=self._tool_fonts).pack(side="left")
        ttk.Button(top, text="O que mudou", command=self._tool_update).pack(side="left", padx=4)
        ttk.Button(top, text="Conferir consistência", command=self._tool_consistency).pack(side="left")
        ttk.Button(top, text="Memória de tradução", command=self._tool_memory).pack(side="left", padx=4)
        ttk.Button(top, text="Copiar relatório de erro", command=self.copy_error_report).pack(side="right")
        box = ttk.Frame(win)
        box.pack(fill="both", expand=True, padx=10)
        self._tools_text = tk.Text(box, wrap="word", bg=G.CARD, fg=G.INK, insertbackground=G.INK, relief="flat", padx=8, pady=8)
        sb = ttk.Scrollbar(box, orient="vertical", command=self._tools_text.yview)
        self._tools_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._tools_text.pack(side="left", fill="both", expand=True)
        self._tools_say("Escolha uma ferramenta acima. Todas trabalham no mod que está aberto.\n\n"
                        "• Sugerir presets: acha nomes do Kenshi original no mod e diz quais presets usar.\n"
                        "• Nomes novos do mod: nomes que o mod cria; decida se mantém ou traduz antes de traduzir.\n"
                        "• Conferir caracteres: acha letras e sinais que a fonte do jogo não desenha.\n"
                        "• O que mudou: mostra o que mudou quando o mod original foi atualizado.\n"
                        "• Memória de tradução: guarda tudo que já foi traduzido e vale para todos os mods; dá para exportar e importar.\n"
                        "• Conferir consistência: acha o mesmo texto traduzido de jeitos diferentes e traduções que não usam o glossário.")
        i18n.apply(win)

    def _tools_say(self, text: str) -> None:
        t = self._tools_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("end", i18n.tr(text))
        t.configure(state="disabled")
        for w in self._tools_btn_row.winfo_children():
            w.destroy()

    def _tools_action(self, label: str, command) -> None:
        ttk.Button(self._tools_btn_row, text=label, command=command).pack(side="left", padx=(0, 6))

    def _tools_project(self):
        if not self._ensure_project():
            return None
        return self.session.project

    def _tool_presets(self) -> None:
        proj = self._tools_project()
        if proj is None:
            return
        presets = {p["id"]: {"nome": p["nome"], "terms": load_preset(p["id"])} for p in presets_for(self.session.cfg.target_lang)[0]}
        found = suggest.suggest_presets([u.source for u in proj.units], presets)
        if not found:
            self._tools_say("Não achei nomes do Kenshi original neste mod. Nenhum preset é necessário.")
            return
        lines = ["Presets que combinam com este mod (do mais ao menos usado):", ""]
        for f in found:
            lines.append(f"• {f['nome']}: {f['termos']} nomes diferentes, {f['hits']} aparições. Ex.: {', '.join(f['exemplos'])}")
        self._tools_say("\n".join(lines))
        ids = [f["id"] for f in found]

        def add() -> None:
            added = 0
            for pid in ids:
                a, _u, _s = self.session.glossary.merge(presets[pid]["terms"], overwrite=False)
                added += a
            self.session.glossary.save(self.session.glossary_file)
            messagebox.showinfo("Presets", f"Adicionados ao glossário: {added} termos (os que você já tinha ficam como estão).")
        self._tools_action("Adicionar esses presets ao glossário", add)

    def _tool_names(self) -> None:
        proj = self._tools_project()
        if proj is None:
            return
        known = set(self.session.glossary.terms)
        for p in presets_for(self.session.cfg.target_lang)[0]:
            known.update(load_preset(p["id"]))
        names = suggest.new_names(proj.units, known)
        if not names:
            self._tools_say("Não achei nomes novos: tudo que parece nome próprio já está no glossário ou nos presets.")
            return
        self._tools_say(f"{len(names)} nomes de registros que não estão no glossário nem nos presets.\n"
                        "Se forem nomes próprios (pessoas, lugares), mantenha como estão para o tradutor não mexer neles.\n\n"
                        + "\n".join(names))

        def keep() -> None:
            for n in names:
                self.session.glossary.set(n, None)
            self.session.glossary.save(self.session.glossary_file)
            messagebox.showinfo("Glossário", f"{len(names)} nomes marcados como “manter como está”.")
        self._tools_action("Manter todos como estão", keep)

    def _tool_consistency(self) -> None:
        from . import consistency
        proj = self._tools_project()
        if proj is None:
            return
        rep = consistency.check(proj.units, self.session.glossary)
        if not rep.total:
            self._tools_say("Tudo consistente: nenhum texto repetido com traduções diferentes e nenhuma tradução fora do glossário.")
            return
        lines = [f"{len(rep.divergences)} textos repetidos com traduções diferentes · {len(rep.misses)} traduções que não usam o glossário.", ""]
        for d in rep.divergences[:30]:
            lines.append(f"• “{d.source[:70]}” ficou assim: " + " | ".join(f"{t[:40]} (×{n})" for t, n in d.versions[:3]))
        if len(rep.divergences) > 30:
            lines.append(f"… e mais {len(rep.divergences) - 30}.")
        if rep.misses:
            lines.append("")
            for m in rep.misses[:30]:
                lines.append(f"• Glossário: “{m.term}” devia ser “{m.expected}” em: {m.source[:60]}")
            if len(rep.misses) > 30:
                lines.append(f"… e mais {len(rep.misses) - 30}.")
        self._tools_say("\n".join(lines))

        def unify_all() -> None:
            n = sum(consistency.unify(proj.units, d) for d in rep.divergences)
            proj.save()
            self.refresh_table()
            messagebox.showinfo("Consistência", f"{n} textos agora usam a versão mais usada.")

        def mark() -> None:
            n = consistency.mark_for_review(proj.units, rep.misses)
            proj.save()
            self.refresh_table()
            messagebox.showinfo("Consistência", f"{n} textos marcados como “Conferir”.")
        if rep.divergences:
            self._tools_action("Usar a versão mais comum em todos", unify_all)
        if rep.misses:
            self._tools_action("Marcar os fora do glossário como Conferir", mark)

    def _tool_memory(self) -> None:
        mem = self.session.memory
        self._tools_say(f"A memória de tradução tem {mem.count()} frases. Ela vale para todos os mods: "
                        "uma frase já traduzida não é traduzida (nem paga) de novo.\n\n"
                        "Exportar salva num arquivo para levar a outro computador. Importar junta um arquivo à memória "
                        "sem trocar o que você já tem.")

        def export() -> None:
            f = filedialog.asksaveasfilename(title="Exportar memória", defaultextension=".json", initialfile="memoria-kenshi.json",
                                             filetypes=[("Memória", "*.json")])
            if f:
                messagebox.showinfo("Memória", f"{mem.export_json(f)} frases exportadas.")

        def imp() -> None:
            f = filedialog.askopenfilename(title="Importar memória", filetypes=[("Memória", "*.json")])
            if not f:
                return
            try:
                n = mem.import_json(f)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Memória", f"Não consegui ler esse arquivo: {e}")
                return
            messagebox.showinfo("Memória", f"{n} frases novas importadas.")
        self._tools_action("Exportar", export)
        self._tools_action("Importar", imp)

    def _font_ranges(self):
        try:
            kd = self.session.cfg.kenshi_dir
            f = Path(kd) / "data" / "gui" / "fonts" / "kenshi_fonts.xml"
            if kd and f.exists():
                return fontcheck.parse_ranges(f.read_text(encoding="utf-8-sig", errors="ignore"))
        except Exception:  # noqa: BLE001
            pass
        return fontcheck.DEFAULT_RANGES

    def _tool_fonts(self) -> None:
        proj = self._tools_project()
        if proj is None:
            return
        ranges = self._font_ranges()
        res = fontcheck.scan(proj.units, ranges)
        if not res["units"]:
            self._tools_say("Tudo certo: as traduções só usam caracteres que a fonte do Kenshi desenha "
                            f"(faixa {ranges[0][0]} a {ranges[0][1]}). Acentos do português estão dentro dela.")
            return
        top = ", ".join(f"{c!r} ×{n}" for c, n in res["chars"].most_common(15))
        self._tools_say(f"{len(res['units'])} textos têm caracteres fora da fonte do jogo (aparecem como espaço ou quadrado).\n\n"
                        f"Mais comuns: {top}\n\n"
                        "Aspas curvas, travessão e reticências costumam ser a causa e podem ser trocados por versões simples.")

        def fix() -> None:
            n, left = fontcheck.fix_typography(proj.units, ranges)
            proj.save()
            self.refresh_table()
            extra = f"\nSem solução automática: {', '.join(repr(c) for c in left)}." if left else ""
            messagebox.showinfo("Caracteres", f"{n} textos corrigidos.{extra}")
            self._tool_fonts()
        self._tools_action("Trocar pontuação por versões simples", fix)

    def _tool_update(self) -> None:
        proj = self._tools_project()
        if proj is None:
            return
        info = proj.update_info
        if not info:
            self._tools_say("Este mod é novo para o programa (ou ainda não foi reaberto depois de atualizar). Nada a comparar.")
            return
        if not info["mod_mudou"]:
            self._tools_say("O arquivo do mod é o mesmo da última vez. Nada mudou.")
            return
        self._tools_say(f"O mod original foi atualizado desde a última vez.\n\n"
                        f"• Textos novos: {info['novos']}\n• Textos que mudaram: {info['mudaram']}\n"
                        f"• Textos que saíram: {info['removidos']}\n\n"
                        "Suas traduções antigas foram mantidas. Os que mudaram aparecem em “Conferir” com a tradução antiga na nota.")

        def run() -> None:
            n = proj.mark_changed_pending()
            proj.save()
            self.refresh_table()
            self._tools_win.destroy()
            self.start_translate(False)
        self._tools_action("Traduzir só o que mudou", run)

    # ------------------------------------------------------------ modo simples
    def open_simple(self) -> None:
        from . import gui as G
        win = tk.Toplevel(self.root)
        win._tip_ctx = "simples"
        win.title(i18n.tr("Modo simples"))
        win.geometry("420x330")
        win.transient(self.root)
        win.configure(bg=G.BG)
        tk.Label(win, bg=G.BG, fg=G.MUTED, wraplength=380, justify="left", text=i18n.tr(
            "Passo 1: escolha o mod na lista da janela principal.\nDepois use os botões abaixo, na ordem.")).pack(anchor="w", padx=16, pady=(14, 8))
        for n, (txt, cmd) in enumerate((
                ("2. Traduzir este mod", lambda: self.start_translate(False)),
                ("3. Instalar no jogo", self.install_mod),
                ("Desfazer: restaurar o original", self.restore_original_ui))):
            ttk.Button(win, text=txt, command=cmd).pack(fill="x", padx=16, pady=5, ipady=8)
        tk.Label(win, bg=G.BG, fg=G.MUTED, textvariable=self.status_var, wraplength=380, justify="left").pack(anchor="w", padx=16, pady=(10, 0))
        i18n.apply(win)
