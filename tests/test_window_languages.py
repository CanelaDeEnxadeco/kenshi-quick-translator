"""Teste da JANELA de verdade: trocar o idioma do mod e o de destino não pode fechar nem quebrar o programa.
Precisa de tela: no Windows é só rodar `python -m unittest tests.test_window_languages -v`.
No Linux: xvfb-run -a python -m unittest tests.test_window_languages -v
Sem tkinter ou sem tela, os testes são pulados (não falham)."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import tkinter as tk
    _root = tk.Tk()
    _root.destroy()
    HAS_TK = True
except Exception:  # noqa: BLE001 - sem tkinter ou sem tela
    HAS_TK = False

if HAS_TK:
    from kenshi_translator_toolkit import FileType, ModFile, RawRecord, TypeCode, dump
    from kenshi_quick_translator import gui
    from kenshi_quick_translator.config import Config
    from kenshi_quick_translator.providers import LANGUAGES
    from kenshi_quick_translator.session import Session


def _pump(root, secs=0.3):
    end = time.time() + secs
    while time.time() < end:
        root.update()
        time.sleep(0.01)


@unittest.skipUnless(HAS_TK, "sem tkinter/tela neste computador")
class JanelaIdiomas(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        data = self.work / "dados"
        data.mkdir()
        self.cfg = Config(provider="simulado", target_lang="pt-BR", tour_done=True)
        self.cfg.save = lambda path=None: None
        self.root = tk.Tk()
        self.errors = []
        with mock.patch.object(gui, "Session", lambda: Session(self.cfg, workdir=data)):
            self.app = gui.App(self.root)
        # qualquer erro dentro de um botão/caixa chega aqui em vez de passar batido
        self.root.report_callback_exception = lambda et, e, tb: self.errors.append(f"{et.__name__}: {e}")
        _pump(self.root, 0.5)

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    def _escolher(self, box, var, code):
        var.set(gui.lang_display(code))
        box.event_generate("<<ComboboxSelected>>")
        _pump(self.root, 0.6)

    def test_trocar_idioma_do_mod_sem_mod_aberto(self):
        for code in ("en", "ru", "auto", "en"):
            self._escolher(self.app.src_box, self.app.src_var, code)
        self.assertEqual(self.errors, [])
        self.assertTrue(self.root.winfo_exists())

    def test_trocar_idioma_do_mod_com_mod_aberto(self):
        mod = self.work / "exemplo.mod"
        mod.write_bytes(_build_mod())
        self.app.load_mod(mod)
        _pump(self.root, 1.0)
        self.assertIsNotNone(self.app.session.project, "o mod não abriu")
        for code in ("ru", "en", "auto", "de", "en"):
            self._escolher(self.app.src_box, self.app.src_var, code)
            _pump(self.root, 0.6)
        self.assertEqual(self.errors, [])
        self.assertTrue(self.root.winfo_exists())
        self.assertIsNotNone(self.app.session.project)

    def test_trocar_idioma_de_destino_pergunta_o_glossario(self):
        chamadas = []
        with mock.patch.object(gui.App, "_glossary_checkpoint", lambda self, gate: chamadas.append(gate) or True):
            for code in ("es", "fr", "pt-BR"):
                self._escolher(self.app.dst_box, self.app.dst_var, code)
        self.assertEqual(self.errors, [])
        self.assertTrue(all(c is False for c in chamadas))
        self.assertGreaterEqual(len(chamadas), 2)

    def test_todos_os_idiomas_de_destino(self):
        with mock.patch.object(gui.App, "_glossary_checkpoint", lambda self, gate: True):
            for code in LANGUAGES:
                if code != "auto":
                    self._escolher(self.app.dst_box, self.app.dst_var, code)
        self.assertEqual(self.errors, [])


    def test_tutoriais_abrem_e_passam_em_todos_os_idiomas_do_programa(self):
        """Boas-vindas -> básico -> avançado, em cada idioma da interface, sem erro e sem deixar moldura para trás."""
        from kenshi_quick_translator import i18n
        try:
            for lang in ("pt", "en", "es", "ru", "zh"):
                i18n.set_language(lang)
                self.app.open_tutorial_menu(first_run=False)
                _pump(self.root, 0.2)
                self.assertIsNotNone(self.app.welcome)
                self.app.welcome.choose("basic")
                _pump(self.root, 0.2)
                self.assertIsNotNone(self.app.tour)
                tour = self.app.tour
                for _ in range(len(tour.steps)):
                    tour.next()
                    _pump(self.root, 0.15)
                self.assertIsNone(self.app.tour)
                self.app.start_tutorial("advanced")
                tour = self.app.tour
                self.assertGreaterEqual(len(tour.steps), 12)
                for _ in range(len(tour.steps)):
                    tour.next()
                    _pump(self.root, 0.15)
                self.assertIsNone(self.app.tour)
                self.assertEqual(tour.ring, [])  # a moldura some ao fechar
        finally:
            i18n.set_language("pt")
        self.assertEqual(self.errors, [])

    def test_tutorial_em_janela_estreita_pula_a_lista_de_mods(self):
        self.root.geometry("760x640")
        _pump(self.root, 0.6)
        self.app.start_tutorial("advanced")
        _pump(self.root, 0.3)
        keys = [k for k, _t, _x in self.app.tour.steps]
        if not self.app.sidebar.winfo_ismapped():  # (a janela tem tamanho mínimo; se não encolheu, não há o que conferir)
            self.assertNotIn("mod_buttons", keys)
        self.app.tour.close()
        self.assertEqual(self.errors, [])


def _rec(i, typecode, name, strings):
    return RawRecord(instance_count=0, typecode=typecode, record_id=0, name=name,
                     string_id=f"{i}-Test.mod", flags=0, strings=strings)


def _build_mod() -> bytes:
    records = [
        _rec(1, TypeCode.WEAPON, "Sword", [("tooltip", "Hit them with the sharp end.")]),
        _rec(3, TypeCode.DIALOGUE_LINE, "Line", [("text", "Welcome to my shop, friend.")]),
    ]
    mod = ModFile(file_type=FileType.SIMPLE_HEADER, version=1, author="", description="",
                  dependencies="", references="", unknown_a=0, records=records)
    return dump(mod)


if __name__ == "__main__":
    unittest.main()
