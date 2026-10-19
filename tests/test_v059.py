"""v0.5.9: nomes de idioma no idioma da interface (com sigla) e mod traduzido com o MESMO nome do original."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:  # sem Tkinter (ex.: Linux de teste) o módulo i18n ainda dá para usar: só as funções de texto
    import tkinter  # noqa: F401
except ImportError:
    for _m in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk", "tkinter.font"):
        sys.modules[_m] = mock.MagicMock()

from kenshi_translator_toolkit import load
from kenshi_translator_toolkit.format.mod_file import RawRecord

from kenshi_quick_translator import i18n
from kenshi_quick_translator.core import (build_translation, install_translation, translate_project,
                                  verify_output)
from kenshi_quick_translator.langdetect import lang_name
from kenshi_quick_translator.locate import KenshiDirs, ORIGINAL_SUFFIX, real_mod_name, scan_mods
from kenshi_quick_translator.project import Project, resolve_project_path
from kenshi_quick_translator.providers import Simulated
from kenshi_quick_translator.session import language_label

from test_core import LINE, make_mod, make_project  # noqa: E402


class LanguageNames(unittest.TestCase):
    def test_nome_e_sigla_em_cada_idioma(self):
        self.assertEqual(lang_name("pt", "pt"), "Português (pt-BR)")
        self.assertEqual(lang_name("pt", "en"), "Portuguese (pt-BR)")
        self.assertEqual(lang_name("pt", "es"), "Portugués (pt-BR)")
        self.assertEqual(lang_name("pt", "ru"), "Португальский (pt-BR)")
        self.assertEqual(lang_name("pt", "zh"), "葡萄牙语 (pt-BR)")
        self.assertEqual(lang_name("en", "pt"), "Inglês (en)")
        self.assertEqual(lang_name("zh", "en"), "Chinese (zh)")
        self.assertEqual(lang_name("und", "en"), "undefined")

    def test_todo_codigo_tem_nome_nos_5_idiomas(self):
        from kenshi_quick_translator.langdetect import _LN
        for code, row in _LN.items():
            self.assertEqual(len(row), 5, code)
            for ui in ("pt", "en", "es", "ru", "zh"):
                self.assertTrue(lang_name(code, ui))

    def test_rotulo_da_lista_muda_com_o_idioma(self):
        counts = {"en": 50, "zh": 40, "und": 3}
        self.assertEqual(language_label(counts, "pt"), "Inglês (en) + Chinês (zh)")
        self.assertEqual(language_label(counts, "en"), "English (en) + Chinese (zh)")
        self.assertEqual(language_label({}, "en"), "undefined")
        self.assertEqual(language_label({}, "pt"), "indefinido")


class SameName(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _kenshi(self, with_original: bytes | None = None) -> Path:
        k = self.tmp / "Kenshi"
        (k / "data").mkdir(parents=True)
        (k / "data" / "mods.cfg").write_text("Test.mod\n")
        if with_original is not None:
            (k / "mods" / "Test").mkdir(parents=True)
            (k / "mods" / "Test" / "Test.mod").write_bytes(with_original)
        return k

    def test_copia_completa_com_mesmo_nome(self):
        proj, mod_path = make_project(self.tmp, [LINE, "Maybe."])
        # um registro que não é texto traduzível também precisa continuar no arquivo gerado
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        self.assertEqual(res.problems, [])
        self.assertEqual(res.path.name, "Test.mod")
        orig, out = load(mod_path.read_bytes()), load(res.path.read_bytes())
        self.assertEqual(len(out.records), len(orig.records))
        self.assertEqual(out.dependencies, orig.dependencies)  # sem se acrescentar como dependência
        self.assertIn("[Kenshi Quick Translator: pt-BR]", out.description)

    def test_recusa_sobrescrever_o_original(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        translate_project(proj, Simulated())
        before = mod_path.read_bytes()
        with self.assertRaises(ValueError):
            build_translation(proj, mod_path, mod_path.parent)
        self.assertEqual(mod_path.read_bytes(), before)

    def test_instalar_guarda_o_original_uma_vez(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        original = mod_path.read_bytes()
        k = self._kenshi(with_original=original)
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        dest, changed = install_translation(k, res.path, "Test.mod")
        self.assertEqual(dest.read_bytes(), res.path.read_bytes())
        backup = dest.with_name("Test.mod" + ORIGINAL_SUFFIX)
        self.assertEqual(backup.read_bytes(), original)
        self.assertFalse(changed)
        # segunda instalação (outro idioma): o backup continua sendo o ORIGINAL, não a tradução anterior
        proj.target_lang = "ru"
        res2 = build_translation(proj, backup, self.tmp / "out2")
        self.assertEqual(res2.path.name, "Test.mod")
        install_translation(k, res2.path, "Test.mod")
        self.assertEqual(backup.read_bytes(), original)
        self.assertIn("[Kenshi Quick Translator: ru]", load(dest.read_bytes()).description)

    def test_lista_usa_o_backup_como_fonte(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        original = mod_path.read_bytes()
        k = self._kenshi(with_original=original)
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        dest, _ = install_translation(k, res.path, "Test.mod")
        entries = [e for e in scan_mods(KenshiDirs(k, None, "teste")) if e.source == "local"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "Test.mod")
        self.assertEqual(entries[0].path.read_bytes(), original)  # lê o original, não a tradução
        self.assertEqual(real_mod_name(entries[0].path.name), "Test.mod")
        # abrir pelo backup dá o mesmo projeto (mesmo nome e mesmo arquivo de progresso)
        p1 = Project.from_mod_file(entries[0].path, self.tmp / "proj2", target_lang="ru")
        self.assertEqual(p1.mod_name, "Test.mod")
        self.assertEqual(p1.path, resolve_project_path(self.tmp / "proj2", dest, "ru"))

    def test_workshop_nao_gera_backup(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        k = self._kenshi()  # nada instalado na pasta do jogo: o original está só no "Workshop"
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        dest, changed = install_translation(k, res.path, "Test.mod")
        self.assertTrue(dest.exists())
        self.assertFalse(dest.with_name("Test.mod" + ORIGINAL_SUFFIX).exists())

    def test_ativa_no_mods_cfg_se_faltava(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        k = self._kenshi()
        (k / "data" / "mods.cfg").write_text("Outro.mod\n")
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        _, changed = install_translation(k, res.path, "Test.mod")
        self.assertTrue(changed)
        self.assertEqual((k / "data" / "mods.cfg").read_text(), "Outro.mod\nTest.mod\n")

    def test_verify_acusa_dependencia_propria(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        from kenshi_translator_toolkit import dump
        m = load(res.path.read_bytes())
        m.dependencies = "Test.mod"
        res.path.write_bytes(dump(m))
        self.assertTrue(any("depende de si mesmo" in p for p in verify_output(res.path, proj)))


class DependentMode(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_arquivo_pequeno_com_dependencia_e_nome_com_idioma(self):
        proj, mod_path = make_project(self.tmp, [LINE, "Maybe."])
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out", mode="dependente")
        self.assertEqual(res.problems, [])
        self.assertEqual(res.path.name, "Test PT-BR.mod")
        out = load(res.path.read_bytes())
        self.assertIn("Test.mod", out.dependencies)
        self.assertLessEqual(len(out.records), len(load(mod_path.read_bytes()).records))

    def test_verificacao_acusa_falta_de_dependencia(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out", mode="dependente")
        from kenshi_translator_toolkit import dump
        m = load(res.path.read_bytes())
        m.dependencies = ""
        res.path.write_bytes(dump(m))
        self.assertTrue(any("dependência" in p for p in verify_output(res.path, proj)))

    def test_instalar_em_pasta_propria_depois_do_original(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        k = self.tmp / "Kenshi"
        (k / "data").mkdir(parents=True)
        (k / "data" / "mods.cfg").write_text("A.mod\nTest.mod\nZ.mod\n")
        (k / "mods" / "Test").mkdir(parents=True)
        (k / "mods" / "Test" / "Test.mod").write_bytes(mod_path.read_bytes())
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out", mode="dependente")
        dest, changed = install_translation(k, res.path, "Test.mod")
        self.assertEqual(dest, k / "mods" / "Test PT-BR" / "Test PT-BR.mod")
        self.assertTrue(changed)
        self.assertEqual((k / "data" / "mods.cfg").read_text(), "A.mod\nTest.mod\nTest PT-BR.mod\nZ.mod\n")
        # o original em Kenshi/mods/Test não foi tocado e não ganhou backup
        self.assertEqual((k / "mods" / "Test" / "Test.mod").read_bytes(), mod_path.read_bytes())
        self.assertFalse((k / "mods" / "Test" / ("Test.mod" + ORIGINAL_SUFFIX)).exists())

    def test_config_padrao_e_gravacao(self):
        from kenshi_quick_translator.config import Config
        self.assertEqual(Config().translation_mode, "completo")
        p = self.tmp / "c.json"
        c = Config(); c.translation_mode = "dependente"; c.save(p)
        self.assertEqual(Config.load(p).translation_mode, "dependente")

    def test_sessao_usa_o_modo_da_configuracao(self):
        from kenshi_quick_translator.config import Config
        from kenshi_quick_translator.session import Session
        proj, mod_path = make_project(self.tmp, [LINE])
        translate_project(proj, Simulated())
        for mode, name in (("completo", "Test.mod"), ("dependente", "Test PT-BR.mod")):
            cfg = Config(); cfg.translation_mode = mode
            sess = Session(cfg, workdir=self.tmp / ("w" + mode))
            sess.project, sess.mod_path = proj, mod_path
            self.assertEqual(sess.build(self.tmp / ("o" + mode)).path.name, name)

    def test_textos_da_opcao_traduzidos(self):
        import ast
        src = (Path(__file__).parent.parent / "kenshi_quick_translator" / "gui.py").read_text(encoding="utf-8")  # sem importar a janela
        found = {}
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("MODE_LABELS", "MODE_NOTE", "CREDITS_TEXT"):
                found[node.targets[0].id] = ast.literal_eval(node.value)
        MODE_LABELS, MODE_NOTE = found["MODE_LABELS"], found["MODE_NOTE"]
        self.assertIn("Kakrain", found["CREDITS_TEXT"])
        self.assertIn("Canela de Enxadeco", found["CREDITS_TEXT"])
        try:
            for code in ("en", "es", "ru", "zh"):
                i18n.set_language(code)
                out = i18n.tr(found["CREDITS_TEXT"])
                self.assertNotEqual(out, found["CREDITS_TEXT"], code)
                self.assertIn("Kakrain", out)
                self.assertIn("Canela de Enxadeco", out)
        finally:
            i18n.set_language("pt")
        try:
            for code in ("en", "es", "ru", "zh"):
                i18n.set_language(code)
                for t in (*MODE_LABELS.values(), MODE_NOTE, "Tipo do mod traduzido:"):
                    self.assertNotEqual(i18n.tr(t), t, (code, t[:30]))
        finally:
            i18n.set_language("pt")


class InstallTextTranslated(unittest.TestCase):
    def test_confirmacao_sem_portugues_nos_outros_idiomas(self):
        text = ("Isto vai:\n• instalar o mod traduzido em C:\\K\\mods, com o MESMO nome do original “X.mod” "
                "(ele ocupa o lugar do original no jogo)\n• guardar o original como “X.mod.original” "
                "nessa mesma pasta, se ainda não houver\n• garantir que “X.mod” está ativo em data/mods.cfg "
                "(é feito um backup do mods.cfg antes).\n\nContinuar?")
        try:
            for code in ("en", "es", "ru", "zh"):
                i18n.set_language(code)
                out = i18n.tr(text)
                for pt in ("Isto vai", "instalar o mod", "MESMO", "guardar o original", "Continuar?", "backup do"):
                    self.assertNotIn(pt, out.replace("¿Continuar?", ""), (code, pt))
                self.assertIn("X.mod.original", out)
        finally:
            i18n.set_language("pt")

    def test_dicas_novas_traduzidas(self):
        try:
            for code in ("en", "es", "ru", "zh"):
                i18n.set_language(code)
                for pt in ("Cria o mod traduzido: uma cópia completa do original com os textos traduzidos e o MESMO nome. Não altera o original.",
                           "Instala o mod traduzido na pasta do Kenshi, no lugar do original (que fica guardado como backup), e garante que ele está no mods.cfg (com backup)."):
                    self.assertNotEqual(i18n.tr(pt), pt, code)
        finally:
            i18n.set_language("pt")


if __name__ == "__main__":
    unittest.main()
