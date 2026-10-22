"""0.6.5: tips.txt e outros .txt de frases da pasta do mod são traduzidos ao instalar (opção)."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_quick_translator.core import install_translation_info
from kenshi_quick_translator.textfiles import find_text_files, translate_text_files

TIPS = ("Too many corpses left lying around will attract predators.\n"
        "Slave shackles can be removed by picking the lock, or finding a saw\n"
        "\n"
        "Pressing the MEDIC button will order the selected characters to heal.\n"
        "Crystal caves may contain rare treasure...\n")
NAMES = "Vivimade Poojar\nBriana Aylwate\nAmamika Wincbick\nGiacar Beacrum\n"


class Fake:
    name = "fake"
    max_batch = 2

    def translate_batch(self, texts, source, target):
        return [f"PT {t}" for t in texts]


class TextFiles(unittest.TestCase):
    def test_acha_so_frases_e_traduz_mantendo_linhas(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "tips.txt").write_bytes(TIPS.replace("\n", "\r\n").encode())
            (d / "namesF.txt").write_text(NAMES)
            files = find_text_files(d)
            self.assertEqual([f.name for f in files], ["tips.txt"])
            out = translate_text_files(files, Fake(), "pt-BR", cancel=threading.Event())
            lines = out["tips.txt"].decode().split("\r\n")
            self.assertEqual(lines[0], "PT Too many corpses left lying around will attract predators.")
            self.assertEqual(lines[2], "")
            self.assertEqual(len(lines), len(TIPS.split("\n")))

    def test_instalacao_grava_o_txt_traduzido(self):
        from test_core import make_mod
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            built = tmp / "X.mod"
            built.write_bytes(make_mod(["a b c"]))
            (tmp / "kenshi" / "data").mkdir(parents=True)
            info = install_translation_info(tmp / "kenshi", built, "X.mod", None, {"tips.txt": b"ola"})
            self.assertEqual((info.dest.parent / "tips.txt").read_bytes(), b"ola")


if __name__ == "__main__":
    unittest.main()
