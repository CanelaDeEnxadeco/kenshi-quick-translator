"""0.7.1: versão e contraste das paletas (o contraste precisa do tkinter; sem ele o teste é pulado)."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kenshi_quick_translator as pkg  # noqa: E402


class Versao(unittest.TestCase):
    def test_versao_igual_no_pyproject(self):
        toml = (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(re.search(r'^version = "([^"]+)"', toml, re.M).group(1), pkg.__version__)


class Contraste(unittest.TestCase):
    def test_botao_de_destaque_legivel_em_todos_os_temas(self):
        try:
            from kenshi_quick_translator import gui
        except Exception:  # noqa: BLE001 - sem tkinter
            self.skipTest("sem tkinter")
        for name, pal in gui.PALETTES.items():
            for key in ("ACCENT", "ACC_ACT"):
                self.assertGreaterEqual(1.05 / (gui._lum(pal[key]) + 0.05), 4.5, f"{name} {key}")

    def test_banner_aurora_dentro_dos_limites(self):
        try:
            from kenshi_quick_translator.galaxy import aurora
        except Exception:  # noqa: BLE001 - sem tkinter
            self.skipTest("sem tkinter")
        vals = [aurora(x, 1300) for x in range(0, 1300, 7)]
        self.assertTrue(0.62 <= min(vals) and max(vals) <= 1.0)
        self.assertGreater(max(vals) - min(vals), 0.1)  # tem manchas de luz de verdade


if __name__ == "__main__":
    unittest.main()
