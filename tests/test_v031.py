"""Idioma da interface, cópia de imagens ao instalar e aviso de troca (sem Tkinter de verdade)."""
import sys
import tempfile
import types
import unittest
from pathlib import Path

for name in ("tkinter", "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox"):  # só para importar i18n sem tela
    sys.modules.setdefault(name, types.ModuleType(name))
tk = sys.modules["tkinter"]
tk.ttk = sys.modules["tkinter.ttk"]; tk.filedialog = sys.modules["tkinter.filedialog"]; tk.messagebox = sys.modules["tkinter.messagebox"]

from kenshi_quick_translator import i18n  # noqa: E402
from kenshi_quick_translator.core import copy_mod_images, install_translation  # noqa: E402
from kenshi_quick_translator.freeproviders import Aggregate  # noqa: E402
from test_aggregate import Fake  # noqa: E402


class I18n(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("pt")

    def test_portugues_nao_muda(self):
        i18n.set_language("pt")
        self.assertEqual(i18n.tr("Instalar no jogo"), "Instalar no jogo")

    def test_ingles_e_espanhol(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("Instalar no jogo"), "Install in game")
        i18n.set_language("es")
        self.assertEqual(i18n.tr("Instalar no jogo"), "Instalar en el juego")

    def test_texto_com_numeros_vira_por_pedacos(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("76 textos pendentes. Clique em “Traduzir este mod”."), "76 texts pending. Click “Translate this mod”.")
        self.assertEqual(i18n.tr("Pronto. 76 traduzidos, 2 para conferir em 3 s."), "Done. 76 translated, 2 to review in 3 s.")

    def test_aviso_do_agregado(self):
        i18n.set_language("en")
        self.assertIn("Switched to Bing", i18n.tr("Google bloqueou (muitos pedidos). Fica de fora por 1 min. Passei para o Bing."))

    def test_desconhecido_fica_igual_e_nomes_de_status_nao_mudam(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("Pendentes"), "Pending")  # agora traduzido; a janela compara pelo texto traduzido
        self.assertEqual(i18n.tr("algo novo qualquer"), "algo novo qualquer")

    def test_todas_as_linhas_tem_tres_idiomas(self):
        for row in i18n.ROWS:
            self.assertEqual(len(row), 3)
            self.assertTrue(all(row), row)


class Imagens(unittest.TestCase):
    def test_instala_com_imagem_renomeada_e_sem_outros_arquivos(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ws = d / "ws" / "1"
            ws.mkdir(parents=True)
            (ws / "Hydro.mod").write_bytes(b"m")
            (ws / "Hydro.png").write_bytes(b"i")
            (ws / "icon.jpg").write_bytes(b"j")
            (ws / "grande.mesh").write_bytes(b"x")
            (d / "out").mkdir()
            built = d / "out" / "Hydro.mod"
            built.write_bytes(b"t")
            (d / "k" / "data").mkdir(parents=True)
            dest, _ = install_translation(d / "k", built, "Hydro.mod", ws)
            names = sorted(p.name for p in dest.parent.iterdir())
            self.assertEqual(names, ["Hydro.mod", "Hydro.png", "grande.mesh", "icon.jpg"])
            self.assertEqual(dest.read_bytes(), b"t")  # o .mod é o traduzido, as imagens/modelos são os do original

    def test_sem_pasta_de_origem_instala_so_o_mod(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            built = d / "X.mod"
            built.write_bytes(b"t")
            (d / "k" / "data").mkdir(parents=True)
            dest, _ = install_translation(d / "k", built, "X.mod")
            self.assertEqual([p.name for p in dest.parent.iterdir()], ["X.mod"])


class Aviso(unittest.TestCase):
    def test_sem_on_event_nao_avisa_mas_troca(self):
        a = Aggregate([Fake("Google", 429), Fake("Bing")], on_event=None)
        self.assertEqual(a.translate_batch(["a"], "en", "pt-BR"), ["Bing:a"])


class Tema(unittest.TestCase):
    def test_paletas_tem_as_mesmas_chaves_e_cores_distintas(self):
        src = (Path(__file__).parent.parent / "kenshi_quick_translator" / "gui.py").read_text(encoding="utf-8")
        ns = {}
        exec(src[src.index("PALETTES: dict"): src.index('THEME = "light"')], ns)
        light, dark = ns["PALETTES"]["light"], ns["PALETTES"]["dark"]
        self.assertEqual(set(light), set(dark))
        for pal in (light, dark):  # cores repetidas atrapalhariam a troca de tema na hora
            self.assertEqual(len(pal), len({v.lower() for v in pal.values()}))


if __name__ == "__main__":
    unittest.main()
