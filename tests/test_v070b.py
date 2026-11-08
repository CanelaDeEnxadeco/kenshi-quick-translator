"""0.7.0: no modo dependente a pasta do original NÃO é copiada (só as imagens)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_quick_translator.core import install_translation_info


class Dependente(unittest.TestCase):
    def make(self, t):
        t = Path(t)
        k = t / "K"; (k / "data").mkdir(parents=True); (k / "mods").mkdir()
        src = t / "orig"; (src / "dll").mkdir(parents=True)
        (src / "Big Mod.mod").write_bytes(b"x")
        (src / "RE_Kenshi.json").write_text("{}")
        (src / "dll" / "plugin.dll").write_bytes(b"MZ")
        (src / "Big Mod.png").write_bytes(b"png")
        built = t / "out"; built.mkdir()
        return k, src, built

    def test_dependente_so_copia_imagem(self):
        with tempfile.TemporaryDirectory() as t:
            k, src, built = self.make(t)
            b = built / "Big Mod PT-BR.mod"; b.write_bytes(b"tr")
            info = install_translation_info(k, b, "Big Mod.mod", src)
            d = info.dest.parent
            self.assertTrue((d / "Big Mod PT-BR.png").is_file())
            self.assertFalse((d / "RE_Kenshi.json").exists())
            self.assertFalse((d / "dll").exists())

    def test_dependente_leva_tips_na_pasta_da_traducao(self):
        with tempfile.TemporaryDirectory() as t:
            k, src, built = self.make(t)
            b = built / "Big Mod PT-BR.mod"; b.write_bytes(b"tr")
            info = install_translation_info(k, b, "Big Mod.mod", src, {"tips.txt": b"dica traduzida"})
            self.assertEqual((info.dest.parent / "tips.txt").read_bytes(), b"dica traduzida")
            self.assertFalse((k / "mods" / "Big Mod").exists())  # a pasta do original nao e criada/tocada

    def test_completo_continua_copiando_tudo(self):
        with tempfile.TemporaryDirectory() as t:
            k, src, built = self.make(t)
            b = built / "Big Mod.mod"; b.write_bytes(b"tr")
            info = install_translation_info(k, b, "Big Mod.mod", src)
            d = info.dest.parent
            self.assertTrue((d / "RE_Kenshi.json").is_file())
            self.assertTrue((d / "dll" / "plugin.dll").is_file())


if __name__ == "__main__":
    unittest.main()


class DependenteComTipsENomes(unittest.TestCase):
    def test_leva_tips_e_names_sem_tocar_no_original(self):
        from kenshi_quick_translator.config import Config
        from kenshi_quick_translator.locate import KenshiDirs
        from kenshi_quick_translator.session import Session
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            kenshi = tmp / "K"; (kenshi / "data").mkdir(parents=True)
            orig = kenshi / "mods" / "Foo"; orig.mkdir(parents=True)
            (orig / "Foo.mod").write_bytes(b"x")
            (orig / "namesM.txt").write_text("Shaku\nTako\nJin\n", encoding="utf-8")
            (orig / "namesF.txt").write_text("Rin\nSau\nMau\n", encoding="utf-8")
            (orig / "tips.txt").write_text("\n".join(["Tip one is a rather long sentence about the game."] * 5), encoding="utf-8")
            cfg = Config(provider="simulado", kenshi_dir=str(kenshi), target_lang="pt-BR", tour_done=True)
            cfg.save = lambda path=None: None
            s = Session(cfg, workdir=tmp / "d")
            dirs = KenshiDirs(kenshi, None, "teste")
            out = s._text_files("Foo.mod", dirs, None, True)
            self.assertIn("namesM.txt", out); self.assertIn("namesF.txt", out)
            self.assertEqual(out["namesM.txt"], (orig / "namesM.txt").read_bytes())  # sem traduzir
            self.assertIn("tips.txt", out)
            cfg.translate_tips_dependent = False
            self.assertEqual(s._text_files("Foo.mod", dirs, None, True), {})
            # modo Completo continua sem levar names
            cfg.translate_text_files = True
            self.assertNotIn("namesM.txt", s._text_files("Foo.mod", dirs, None, False))


class NomesEmOutroAlfabeto(unittest.TestCase):
    def test_russo_vira_latino_so_quando_destino_e_latino(self):
        from kenshi_quick_translator.translit import foreign_scripts, latinize_line, latinize_names
        raw = "Шаку\r\nДжимбад\r\nГораций\r\nde Zerka\r\n".encode("utf-8")
        new, n = latinize_names(raw, "pt-BR")
        self.assertEqual(n, 3)
        self.assertEqual(new.decode().split("\r\n"), ["Shaku", "Jimbad", "Goratsiy", "de Zerka", ""])
        same, n2 = latinize_names(raw, "ru")  # destino em russo: o alfabeto é o do idioma, não mexe
        self.assertEqual((same, n2), (raw, 0))
        lat = "Tako\nJin\n".encode()
        self.assertEqual(latinize_names(lat, "pt-BR"), (lat, 0))  # já latino: mesmos bytes
        self.assertFalse(foreign_scripts("José Ñandú", "en"))  # acentos latinos não contam

    def test_grego_kana_hangul(self):
        from kenshi_quick_translator.translit import latinize_line
        self.assertEqual(latinize_line("Αλέξανδρος"), "Alexandros")
        self.assertEqual(latinize_line("ユーゴ"), "Yugo")
        self.assertEqual(latinize_line("シャチ"), "Shachi")
        self.assertEqual(latinize_line("김민수"), "Gimminsu")

    def test_nome_nunca_some(self):
        from kenshi_quick_translator.translit import latinize_line
        self.assertEqual(latinize_line("ъь"), "ъь")  # só letras mudas: fica como está

    def test_instala_names_convertido_no_dependente(self):
        from kenshi_quick_translator.config import Config
        from kenshi_quick_translator.locate import KenshiDirs
        from kenshi_quick_translator.session import Session
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            kenshi = tmp / "K"; (kenshi / "data").mkdir(parents=True)
            orig = kenshi / "mods" / "Foo"; orig.mkdir(parents=True)
            (orig / "Foo.mod").write_bytes(b"x")
            (orig / "namesM.txt").write_text("Шаку\nДжин\nТако\n", encoding="utf-8")
            (orig / "namesF.txt").write_text("Rin\nSau\n", encoding="utf-8")
            cfg = Config(provider="simulado", kenshi_dir=str(kenshi), target_lang="pt-BR", tour_done=True)
            cfg.save = lambda path=None: None
            s = Session(cfg, workdir=tmp / "d")
            out = s._text_files("Foo.mod", KenshiDirs(kenshi, None, "teste"), None, True)
            self.assertEqual(out["namesM.txt"].decode(), "Shaku\nJin\nTako\n")
            self.assertEqual(out["namesF.txt"], b"Rin\nSau\n")
            self.assertEqual(s.last_latinized, {"namesM.txt": 3})
            self.assertEqual((orig / "namesM.txt").read_text(encoding="utf-8").splitlines()[0], "Шаку")  # original intacto
            cfg.latinize_names = False
            self.assertEqual(s._text_files("Foo.mod", KenshiDirs(kenshi, None, "teste"), None, True)["namesM.txt"],
                             (orig / "namesM.txt").read_bytes())

    def test_chines_com_unidecode(self):
        try:
            import unidecode  # noqa: F401
        except ImportError:
            self.skipTest("sem unidecode")
        from kenshi_quick_translator.translit import latinize_line
        self.assertEqual(latinize_line("张伟"), "Zhang Wei")
