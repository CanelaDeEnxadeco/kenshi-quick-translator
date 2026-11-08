"""v0.7.4.8: todo botão e caixa de marcar do programa precisa ter dica ao passar o mouse.

Lê o código-fonte (sem abrir janela, sem Tkinter) e confere que cada botão com texto fixo tem uma dica:
na tabela de qualquer janela, na global, na tabela antiga (TIPS_BY_TEXT), numa `Tip` própria ou em `_tip_text`.
Se você criar um botão novo e este teste falhar, acrescente a dica em kenshi_quick_translator/ui_tips.py.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kenshi_quick_translator import ui_tips  # noqa: E402
from kenshi_quick_translator.ui_extra import TIPS_BY_TEXT  # noqa: E402

FILES = ("gui.py", "ui_actions.py", "ui_tools.py")
KINDS = {"Button", "Checkbutton", "Radiobutton"}
# botões cujo texto é uma variável/f-string; a dica deles é ligada no código (ver _tip_text) ou eles se explicam
DYNAMIC_OK = {"label", "go", "txt", "text", "hint"}


def _literal_text(node: ast.AST):
    """'texto', i18n.tr('texto') -> 'texto'; qualquer outra coisa (variável, f-string) -> None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "tr"
            and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
        return node.args[0].value
    return None


def collect_buttons():
    found = []
    for name in FILES:
        path = ROOT / "kenshi_quick_translator" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in KINDS):
                for kw in node.keywords:
                    if kw.arg == "text":
                        found.append((name, node.lineno, _literal_text(kw.value)))
    for name in ("ui_tools.py",):  # botões criados por _tools_action("texto", ...)
        tree = ast.parse((ROOT / "kenshi_quick_translator" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "_tools_action"
                    and node.args):
                found.append((name, node.lineno, _literal_text(node.args[0])))
    return found


# Botões com dica ligada de outro jeito (conferido em test_excecoes_existem_no_codigo)
EXCECOES = {"Limpar dados…", "▲", "▼"}


def has_tip(text: str) -> bool:
    if text in EXCECOES:
        return True
    cands = [text]
    if any(ui_tips.find_tip(ctx, cands) for ctx in list(ui_tips.CONTEXT_TIPS) + [""]):
        return True
    return any(key in text for key, _tip in TIPS_BY_TEXT)


class DicasDosBotoesTests(unittest.TestCase):
    def test_todo_botao_com_texto_fixo_tem_dica(self):
        sem = [(f, n, t) for f, n, t in collect_buttons() if t is not None and t.strip() and not has_tip(t)]
        self.assertEqual(sem, [], "Botões sem dica (arquivo, linha, texto): " + repr(sem))

    def test_excecoes_existem_no_codigo(self):
        src = (ROOT / "kenshi_quick_translator" / "gui.py").read_text(encoding="utf-8")
        self.assertIn("tip(clean_btn,", src)  # "Limpar dados…" tem Tip própria
        for nome in ("TIP_FREE_UP", "TIP_FREE_DOWN", "TIP_LIST_UP", "TIP_LIST_DOWN", "TIP_MULTI_LANG"):
            self.assertIn(f"._tip_text = {nome}", src)  # setas e idiomas do mod

    def test_acha_botoes(self):
        # garante que a auditoria enxerga os botões (se o código mudar de forma, este teste avisa)
        textos = [t for _f, _n, t in collect_buttons() if t]
        self.assertGreater(len(textos), 60)
        self.assertIn("→  Copiar mod para a pasta do jogo", textos)  # (0.7.6: "Abrir pasta do mod" virou item do menu "Mais ▾")
        self.assertIn("Traduzir só o que mudou", textos)

    def test_toda_dica_tem_as_4_traducoes(self):
        for row in ui_tips.TIPS:
            self.assertEqual(len(row), 7, row[1])
            ctx, key, pt, en, es, ru, zh = row
            for lang, txt in (("en", en), ("es", es), ("ru", ru), ("zh", zh)):
                self.assertTrue(txt.strip(), f"{key}: falta {lang}")
            self.assertNotEqual(pt, en, f"{key}: dica em inglês igual à do português")
            self.assertLessEqual(len(pt), 200, f"{key}: dica longa demais")

    def test_mesma_dica_nao_muda_de_traducao(self):
        vistos = {}
        for _ctx, key, pt, en, es, ru, zh in ui_tips.TIPS:
            if pt in vistos:
                self.assertEqual(vistos[pt], (en, es, ru, zh), f"{key}: mesma dica com traduções diferentes")
            vistos[pt] = (en, es, ru, zh)

    def test_dica_certa_por_janela(self):
        f = ui_tips.find_tip
        self.assertIn("glossário", f("glossario", ["Remover"]))
        self.assertIn("serviço", f("servicos", ["Remover"]))
        self.assertEqual(f("", ["Remover"]), "")  # sem janela, "Remover" é ambíguo: sem dica
        self.assertTrue(f("", ["▶  Tutorial"]))
        self.assertTrue(f("welcome", ["Tutorial avançado"]))
        self.assertTrue(f("", ["Segunda passada nos “Conferir”…"]))
        self.assertTrue(f("ferramentas", ["Exportar"]))

    def test_comparacao_ignora_icone_atalho_e_reticencias(self):
        n = ui_tips.norm
        self.assertEqual(n("⟳ Atualizar (F5)"), "Atualizar")
        self.assertEqual(n("Gerar mod de tradução…  (F6)"), "Gerar mod de tradução")
        self.assertEqual(n("■  Parar  (Esc)"), "Parar")
        self.assertEqual(n("▶▶  Traduzir selecionados  (Ctrl+Shift+T)"), "Traduzir selecionados")

    def test_traducao_do_texto_do_botao_tambem_acha_a_dica(self):
        # janelas que criam o botão já traduzido (ui_actions usa i18n.tr no texto)
        tr = {"Tentar de novo": "Try again"}.get
        self.assertTrue(ui_tips.find_tip("erro_servico", ["Try again"], lambda s: tr(s, s)))


if __name__ == "__main__":
    unittest.main()
