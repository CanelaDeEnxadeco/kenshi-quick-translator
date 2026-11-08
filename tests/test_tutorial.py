"""v0.7.5: tutoriais básico e avançado, boas-vindas e polimento da janela (parte sem Tkinter).

Confere os textos (5 idiomas), os alvos que o gui.py conhece e que a janela registra, e que os botões novos têm dica.
A parte que abre a janela de verdade fica em tests/test_window_languages.py (precisa de tela).
"""
import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kenshi_quick_translator import i18n, tutorial, ui_tips  # noqa: E402

GUI = (ROOT / "kenshi_quick_translator" / "gui.py").read_text(encoding="utf-8")


class Textos(unittest.TestCase):
    def test_todo_texto_tem_os_cinco_idiomas(self):
        for row in tutorial.MORE_TUTORIAL:
            self.assertEqual(len(row), 5, row[0])
            for col in row:
                self.assertTrue(col.strip(), row[0])
            self.assertNotEqual(row[0], row[1], f"sem tradução em inglês: {row[0][:40]}") if row[0] not in (
                "▶  Tutorial", "Tutorial") else None

    def test_traducao_funciona_pelo_i18n(self):
        try:
            for lang in ("en", "es", "ru", "zh"):
                i18n.set_language(lang)
                for _k, title, text in (*tutorial.BASIC, *tutorial.ADVANCED):
                    if not (lang == "es" and title[0] == title[2]):  # em espanhol alguns títulos são iguais
                        self.assertNotEqual(i18n.tr(title[0]), title[0], (lang, title[0]))
                    self.assertNotEqual(i18n.tr(text[0]), text[0], (lang, title[0]))
            i18n.set_language("zh")
            self.assertEqual(i18n.tr(tutorial.BASIC[0][1][0]), tutorial.BASIC[0][1][4])
        finally:
            i18n.set_language("pt")

    def test_mesmos_numeros_e_teclas_em_todos_os_idiomas(self):
        """Atalhos e números do português precisam aparecer iguais nas outras línguas (F5, Ctrl+T, ...)."""
        pat = re.compile(r"F\d+|Ctrl\+Enter|Ctrl\+Shift\+T|Ctrl\+[A-Z]\b|Ctrl−|Esc|mods\.cfg|erros\.log|Poedit|\.mod|\.json")
        for _k, _title, text in (*tutorial.BASIC, *tutorial.ADVANCED):
            want = sorted(set(pat.findall(text[0])))
            for n, lang in ((1, "en"), (2, "es"), (3, "ru"), (4, "zh")):
                got = set(pat.findall(text[n]))
                for w in want:
                    self.assertIn(w, got, f"{lang}: falta {w} em {text[0][:40]}")

    def test_marcas_de_lista_iguais(self):
        for _k, _title, text in (*tutorial.BASIC, *tutorial.ADVANCED):
            n = text[0].count("\n•")
            for i, lang in enumerate(("en", "es", "ru", "zh"), start=1):
                self.assertEqual(text[i].count("\n•"), n, f"{lang}: linhas diferentes em {text[0][:40]}")

    def test_tamanho_cabe_na_janelinha(self):
        for _k, _title, text in (*tutorial.BASIC, *tutorial.ADVANCED):
            for col in text:
                self.assertLessEqual(len(col), 700, col[:50])

    def test_numeros_dos_passos(self):
        self.assertEqual(len(tutorial.basic_steps()), 6)
        self.assertGreaterEqual(len(tutorial.advanced_steps()), 15)
        self.assertEqual(tutorial.steps_for("advanced"), tutorial.advanced_steps())
        self.assertEqual(tutorial.steps_for("qualquer"), tutorial.basic_steps())


class Alvos(unittest.TestCase):
    KNOWN_IN_TUT_TARGET = {"mods", "help", "tutorial", "settings"}

    def test_todo_alvo_existe_na_janela(self):
        registered = set(re.findall(r'self\.tt\["(\w+)"\]\s*=', GUI))
        cards = {"one", "how", "review", "mods"}
        for kind in ("basic", "advanced"):
            for key, _t, _x in tutorial.steps_for(kind):
                self.assertTrue(key in registered or key in cards or key in self.KNOWN_IN_TUT_TARGET,
                                f"{kind}: alvo '{key}' não é registrado em gui.py")

    def test_botao_do_topo_e_boas_vindas_no_codigo(self):
        for frag in ("self.btn_tutorial", "class Welcome", "def open_tutorial_menu", "def start_tutorial",
                     "self.btn_settings"):
            self.assertIn(frag, GUI)
        self.assertNotIn("Passo a passo\"", GUI)

    def test_gui_compila_e_nao_usa_mais_tour_antigo(self):
        ast.parse(GUI)
        self.assertNotIn("TOUR_STEPS", GUI)

    def test_dicas_dos_botoes_novos(self):
        f = ui_tips.find_tip
        for ctx, txt in (("", "▶  Tutorial"), ("welcome", "Tutorial básico"), ("welcome", "Tutorial avançado"),
                         ("welcome", "Agora não, vou explorar sozinho"), ("welcome", "Não mostrar isto ao abrir o programa"),
                         ("tour", "Ver o tutorial avançado"), ("tour", "Concluir")):
            self.assertTrue(f(ctx, [txt]), txt)

    def test_botoes_laterais_continuam_na_grade(self):
        # 0.7.6: o que se usa pouco foi para o menu "Mais ▾"; o resto continua em botões na grade
        for txt in ("Copiar mod para a pasta do jogo", "Abrir arquivo…", "Pasta do Kenshi…"):
            self.assertRegex(GUI, r'ttk\.Button\(bb, text="[^"]*%s"' % re.escape(txt))
        for txt in ("Abrir pasta do mod", "Zerar tradução deste mod", "Abrir pasta dos projetos"):
            self.assertIn('label=i18n.tr("%s")' % txt, GUI)

    def test_linha_de_baixo_dividida_em_duas(self):
        self.assertIn('ob2 = ttk.Frame(c3', GUI)
        self.assertIn("(ob2, (10, 0))", GUI)


if __name__ == "__main__":
    unittest.main()
