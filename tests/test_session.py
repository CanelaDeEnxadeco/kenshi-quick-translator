"""Testes da lógica da janela (sem abrir nenhuma tela)."""

import tempfile
import unittest
from pathlib import Path

from kenshi_quick_translator.config import Config
from kenshi_quick_translator.locate import find_kenshi, is_kenshi_dir, scan_mods
from kenshi_quick_translator.project import ATTENTION, AUTO, PENDING, REVIEWED
from kenshi_quick_translator.providers import Simulated
from kenshi_quick_translator.session import Session

from test_core import LINE, make_mod


class SessionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.cfg = Config()
        self.cfg.save = lambda path=None: None  # não grava nada fora da pasta de teste
        self.s = Session(self.cfg, workdir=self.tmp / "dados")
        self.mod = self.tmp / "Test.mod"
        self.mod.write_bytes(make_mod([LINE, "Maybe.", "Hello there."]))

    def tearDown(self):
        self.s.close()
        self._tmp.cleanup()

    def test_open_translate_edit_build(self):
        proj = self.s.open_mod(self.mod)
        self.assertEqual(len(proj.units), 3)
        self.s.translate(Simulated())
        self.assertEqual(sum(1 for u in proj.units if u.status == AUTO), 3)

        # revisão manual: marcador errado é recusado, certo é aceito
        with self.assertRaises(ValueError):
            self.s.edit(0, "Por que você iria com esses insetos?")
        self.s.edit(0, "Por que você iria /TEAMUP/ com esses insetos? /GETLOST/ /TRASH/!")
        self.assertEqual(proj.units[0].status, REVIEWED)

        res = self.s.build(self.tmp / "out")
        self.assertEqual(res.problems, [])
        self.assertTrue(res.path.exists())

    def test_edit_is_learned_by_memory(self):
        self.s.open_mod(self.mod)
        self.s.edit(1, "Talvez.")
        self.assertEqual(self.s.memory.get("Maybe.", "pt-BR"), "Talvez.")

    def test_filters_and_search(self):
        self.s.open_mod(self.mod)
        self.assertEqual(len(self.s.visible_units("pendente")), 3)
        self.s.edit(1, "Talvez.")
        self.assertEqual(len(self.s.visible_units("revisada")), 1)
        self.assertEqual([u.source for _, u in self.s.visible_units("todos", "hello")], ["Hello there."])
        self.assertEqual(self.s.visible_units("atencao"), [])

    def test_check_translation_messages(self):
        self.s.open_mod(self.mod)
        u = self.s.project.units[0]
        ok, msg = self.s.check_translation(u, "x /TEAMUP/ /GETLOST/ /TRASH/")
        self.assertTrue(ok)
        ok, msg = self.s.check_translation(u, "sem nada")
        self.assertFalse(ok)
        self.assertIn("faltando", msg)
        ok, msg = self.s.check_translation(u, "")
        self.assertTrue(ok)

    def test_changing_target_language_opens_separate_project(self):
        self.s.open_mod(self.mod)
        self.s.edit(1, "Talvez.")
        self.s.set_languages("auto", "es")
        self.assertEqual(self.s.project.units[1].status, PENDING)  # outro idioma = outro projeto
        self.s.set_languages("auto", "pt-BR")
        self.assertEqual(self.s.project.units[1].status, REVIEWED)  # o trabalho em pt-BR continua lá

    def test_detect_language_from_content(self):
        self.assertEqual(self.s.detect_mod_language(self.mod)[0], "en")

    def test_user_glossary_file_created_once(self):
        path = self.s.ensure_glossary_file()
        self.assertTrue(path.exists())
        self.assertIn("Holy Nation", path.read_text(encoding="utf-8"))


class LocateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def fake_install(self) -> Path:
        steamapps = self.tmp / "SteamLibrary" / "steamapps"
        game = steamapps / "common" / "Kenshi"
        (game / "data").mkdir(parents=True)
        (game / "kenshi_x64.exe").write_bytes(b"")
        (game / "mods" / "Alpha").mkdir(parents=True)
        (game / "mods" / "Alpha" / "Same.mod").write_bytes(b"1")
        ws = steamapps / "workshop" / "content" / "233860" / "12345"
        ws.mkdir(parents=True)
        (ws / "Same.mod").write_bytes(b"22")  # mesmo nome de arquivo, outro mod
        return game

    def test_manual_path_and_workshop_derived(self):
        game = self.fake_install()
        dirs = find_kenshi(str(game))
        self.assertEqual(dirs.kenshi, game)
        self.assertIsNotNone(dirs.workshop)

    def test_same_filename_in_two_places_is_not_overwritten(self):
        dirs = find_kenshi(str(self.fake_install()))
        mods = scan_mods(dirs)
        self.assertEqual(sorted(m.source for m in mods), ["local", "workshop"])
        self.assertEqual(len({m.path for m in mods}), 2)

    def test_wrong_folder_rejected(self):
        self.assertFalse(is_kenshi_dir(self.tmp))
        self.assertTrue(is_kenshi_dir(self.fake_install()))


if __name__ == "__main__":
    unittest.main()
