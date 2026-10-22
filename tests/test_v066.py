"""0.6.6 (parte 1): arquivo de idioma .mo do mod juntado ao idioma do jogo."""
import gettext
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_quick_translator import mofile  # noqa: E402
from kenshi_quick_translator.core import install_translation_info  # noqa: E402
from kenshi_quick_translator.localefiles import (  # noqa: E402
    aliases, find_game_catalog, find_mod_catalogs, matches_language, merge_for_install)

HDR_PT = "Content-Type: text/plain; charset=UTF-8\nLanguage: pt_BR\nPlural-Forms: nplurals=2; plural=(n > 1);\n"
HDR_EN = "Content-Type: text/plain; charset=UTF-8\n"


def mo(entries, header=HDR_EN):
    return mofile.write_mo(mofile.Catalog(entries=entries, header=header))


class Fake:
    name = "fake"
    max_batch = 5

    def translate_batch(self, texts, source, target):
        return [f"PT {t}" for t in texts]


class Formato(unittest.TestCase):
    def test_gravado_e_lido_pelo_gettext_do_python(self):
        data = mo({"New Game": "Novo jogo", "Katanas": "Sabres de luz", "Ação": "Ação ✓"}, HDR_PT)
        t = gettext.GNUTranslations(io.BytesIO(data))
        self.assertEqual(t.gettext("New Game"), "Novo jogo")
        self.assertEqual(t.gettext("Ação"), "Ação ✓")
        cat = mofile.read_mo(data)
        self.assertEqual(cat.language, "pt_BR")
        self.assertEqual(len(cat), 3)

    def test_arquivo_ruim(self):
        with self.assertRaises(mofile.MoError):
            mofile.read_mo(b"isto nao e um mo, de jeito nenhum, nada" * 3)

    def test_merge_mod_vence_e_resto_vem_do_jogo(self):
        game = mofile.Catalog({"New Game": "Novo jogo", "Katanas": "Katanas"}, HDR_PT)
        mod = mofile.Catalog({"Katanas": "Lightsabers", "Vazio": ""}, HDR_EN)
        out = mofile.merge(game, mod, {"Katanas": "Sabres de luz"})
        self.assertEqual(out.entries, {"New Game": "Novo jogo", "Katanas": "Sabres de luz"})
        self.assertIn("pt_BR", out.header)


class Idiomas(unittest.TestCase):
    def test_nomes_do_idioma(self):
        self.assertTrue({"pt-br", "pt_br", "ptbr", "pt", "portuguese", "brazil"} <= aliases("pt-BR"))
        self.assertTrue(matches_language("data/locale/pt_BR", "", "pt-BR"))
        self.assertTrue(matches_language("data/locale/Portuguese", "", "pt-BR"))
        self.assertTrue(matches_language("x", "pt_BR", "pt-BR"))
        self.assertFalse(matches_language("data/locale/en", "", "pt-BR"))
        self.assertFalse(matches_language("data/locale/spanish", "es_ES", "pt-BR"))


def montar(tmp, game_langs=("en", "pt_BR")):
    kenshi = tmp / "kenshi"
    for lang in game_langs:
        d = kenshi / "data" / "locale" / lang
        d.mkdir(parents=True)
        hdr = HDR_PT if lang == "pt_BR" else HDR_EN
        text = {"New Game": "Novo jogo", "Katanas": "Katanas"} if lang == "pt_BR" else {"New Game": "New Game"}
        (d / "main.mo").write_bytes(mo(text, hdr))
    modf = tmp / "mod"
    (modf / "locale" / "en").mkdir(parents=True)
    (modf / "locale" / "en" / "main.mo").write_bytes(mo({"Katanas": "Lightsabers", "Martial arts": "The Force"}))
    return kenshi, modf


class Juntar(unittest.TestCase):
    def test_acha_o_do_jogo_no_idioma_certo(self):
        with tempfile.TemporaryDirectory() as t:
            kenshi, modf = montar(Path(t))
            self.assertEqual([m.rel for m in find_mod_catalogs(modf)], ["locale/en/main.mo"])
            g = find_game_catalog(kenshi, "pt-BR", "main.mo")
            self.assertEqual(g.parent.name, "pt_BR")
            self.assertIsNone(find_game_catalog(kenshi, "ja", "main.mo"))  # não chuta outro idioma
            self.assertIsNone(find_game_catalog(None, "pt-BR", "main.mo"))

    def test_junta_traduz_e_nao_acha_sem_pacote(self):
        with tempfile.TemporaryDirectory() as t:
            kenshi, modf = montar(Path(t))
            res = merge_for_install(modf, kenshi, Fake(), "pt-BR", "en")
            self.assertEqual(len(res), 1)
            m = res[0]
            self.assertEqual((m.mod_texts, m.translated, m.game_texts), (2, 2, 2))
            cat = mofile.read_mo(m.data)
            self.assertEqual(cat.entries["New Game"], "Novo jogo")           # menu do jogo preservado
            self.assertEqual(cat.entries["Katanas"], "PT Lightsabers")        # texto do mod, traduzido
            self.assertEqual(cat.entries["Martial arts"], "PT The Force")
            # sem pacote do jogo naquele idioma: não mexe em nada
            self.assertEqual(merge_for_install(modf, kenshi, Fake(), "ja", "en"), [])

    def test_sem_servico_ainda_junta_com_o_texto_do_mod(self):
        with tempfile.TemporaryDirectory() as t:
            kenshi, modf = montar(Path(t))
            m = merge_for_install(modf, kenshi, None, "pt-BR", "en")[0]
            cat = mofile.read_mo(m.data)
            self.assertEqual(cat.entries["New Game"], "Novo jogo")
            self.assertEqual(cat.entries["Katanas"], "Lightsabers")

    def test_instalacao_grava_com_pasta_e_guarda_o_original(self):
        from test_core import make_mod
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            built = tmp / "X.mod"
            built.write_bytes(make_mod(["a b c"]))
            (tmp / "kenshi" / "data").mkdir(parents=True)
            src = tmp / "src"
            (src / "locale" / "en").mkdir(parents=True)
            old = mo({"Katanas": "Lightsabers"})
            (src / "locale" / "en" / "main.mo").write_bytes(old)
            new = mo({"Katanas": "Sabres", "New Game": "Novo jogo"}, HDR_PT)
            info = install_translation_info(tmp / "kenshi", built, "X.mod", src, {"locale/en/main.mo": new})
            f = info.dest.parent / "locale" / "en" / "main.mo"
            self.assertEqual(f.read_bytes(), new)
            self.assertEqual((f.parent / "main.mo.original").read_bytes(), old)
            install_translation_info(tmp / "kenshi", built, "X.mod", src, {"locale/en/main.mo": new})  # de novo
            self.assertEqual((f.parent / "main.mo.original").read_bytes(), old)


class PacoteDeIdioma(unittest.TestCase):
    def _montar(self, tmp):
        kenshi = tmp / "kenshi"
        lang = kenshi / "locale" / "pt_BR"
        (lang / "LC_MESSAGES").mkdir(parents=True)
        game = mo({"Katanas": "Katanas", "Male": "Masculino", "Crossbows": "Bestas"}, HDR_PT)
        (lang / "main.mo").write_bytes(game)
        (lang / "LC_MESSAGES" / "main.mo").write_bytes(game)
        (lang / "gamedata.mo").write_bytes(b"GAMEDATA")
        (lang / "pt_BR.translation").write_bytes(b"TRANSLATION")
        (lang / "tips.txt").write_text("dicas do jogo")
        (lang / "main.po").write_text("po")
        dest = kenshi / "mods" / "Foo"
        (dest / "locale" / "en_GB" / "LC_MESSAGES").mkdir(parents=True)
        (dest / "locale" / "en_GB" / "LC_MESSAGES" / "main.mo").write_bytes(mo({"Katanas": "Lightsabers"}))
        return kenshi, dest

    def test_pacote(self):
        from kenshi_quick_translator.localefiles import build_locale_pack
        with tempfile.TemporaryDirectory() as t:
            kenshi, dest = self._montar(Path(t))
            files = build_locale_pack(dest, kenshi, Fake(), "pt-BR", "en")
            self.assertIn("locale/pt_BR/gamedata.mo", files)
            self.assertEqual(files["locale/pt_BR/pt_BR.translation"], b"TRANSLATION")
            self.assertNotIn("locale/pt_BR/tips.txt", files)
            self.assertNotIn("locale/pt_BR/main.po", files)
            for rel in ("locale/pt_BR/main.mo", "locale/pt_BR/LC_MESSAGES/main.mo"):
                cat = mofile.read_mo(files[rel])
                self.assertEqual(cat.entries["Male"], "Masculino")
                self.assertEqual(cat.entries["Crossbows"], "Bestas")
                self.assertIn("Katanas", cat.entries)
                self.assertNotEqual(cat.entries["Katanas"], "Katanas")  # veio do mod

    def test_sem_idioma_no_jogo_nao_mexe(self):
        from kenshi_quick_translator.localefiles import build_locale_pack
        with tempfile.TemporaryDirectory() as t:
            kenshi, dest = self._montar(Path(t))
            self.assertEqual(build_locale_pack(dest, kenshi, None, "ja", "en"), {})
            self.assertEqual(build_locale_pack(dest, Path(t) / "nada", None, "pt-BR", "en"), {})


class InstalaPacote(unittest.TestCase):
    def test_instala_e_restaura(self):
        from kenshi_quick_translator.config import Config
        from kenshi_quick_translator.locate import KenshiDirs
        from kenshi_quick_translator.restore import _restore_locale
        from kenshi_quick_translator.session import Session
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            kenshi, dest = PacoteDeIdioma()._montar(tmp)
            cfg = Config(provider="simulado", kenshi_dir=str(kenshi), target_lang="pt-BR", tour_done=True)
            cfg.save = lambda path=None: None
            s = Session(cfg, workdir=tmp / "d")
            dirs = KenshiDirs(kenshi, None, "teste")
            n = s._install_locale("Foo", dirs)
            self.assertGreater(n, 3)
            self.assertTrue((dest / "locale_off" / "en_GB" / "LC_MESSAGES" / "main.mo").is_file())  # original guardada
            self.assertTrue((dest / "locale" / "pt_BR" / "gamedata.mo").is_file())
            self.assertGreater(s._install_locale("Foo", dirs), 3)  # instalar de novo funciona
            self.assertTrue((dest / "locale_off" / "en_GB").is_dir())
            cfg.translate_locale_files = False
            self.assertEqual(s._install_locale("Foo", dirs), 0)
            _restore_locale(dest)
            self.assertTrue((dest / "locale" / "en_GB" / "LC_MESSAGES" / "main.mo").is_file())
            self.assertFalse((dest / "locale_off").exists())
            self.assertFalse((dest / "locale" / "pt_BR").exists())


if __name__ == "__main__":
    unittest.main()
