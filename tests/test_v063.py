"""0.6.3: novo nome (Kenshi Quick Translator), migração da pasta de dados e marca antiga reconhecida."""
import tempfile
import unittest
from pathlib import Path

import kenshi_quick_translator
from kenshi_quick_translator import config, core


class Renome(unittest.TestCase):
    def test_pacote_e_versao(self):
        self.assertTrue(kenshi_quick_translator.__version__)
        self.assertTrue(str(config.app_dir()).endswith("KenshiQuickTranslator"))

    def test_migra_pasta_antiga_copiando(self):
        with tempfile.TemporaryDirectory() as t:
            old, new = Path(t, "KenshiTradutor"), Path(t, "KenshiQuickTranslator")
            (old / "projetos").mkdir(parents=True)
            (old / "projetos" / "A.ktproj.json").write_text("{}")
            (old / "memoria.sqlite").write_bytes(b"db")
            config._migrated = False
            config._migrate_old_folder(old, new)
            self.assertTrue((new / "projetos" / "A.ktproj.json").exists())
            self.assertTrue((new / "memoria.sqlite").exists())
            self.assertTrue((old / "memoria.sqlite").exists(), "a antiga não pode ser apagada")

    def test_nao_sobrescreve_pasta_nova(self):
        with tempfile.TemporaryDirectory() as t:
            old, new = Path(t, "KenshiTradutor"), Path(t, "KenshiQuickTranslator")
            old.mkdir(); (old / "x.txt").write_text("velho")
            new.mkdir(); (new / "y.txt").write_text("novo")
            config._migrated = False
            config._migrate_old_folder(old, new)
            self.assertFalse((new / "x.txt").exists())
            self.assertEqual((new / "y.txt").read_text(), "novo")

    def test_marca_antiga_e_nova_reconhecidas(self):
        old = "Desc\n[Kenshi Tradutor: pt-BR]"
        new = "Desc\n[Kenshi Quick Translator: pt-BR]"
        self.assertEqual(core._MARK_RE.sub("", old), "Desc")
        self.assertEqual(core._MARK_RE.sub("", new), "Desc")


if __name__ == "__main__":
    unittest.main()
