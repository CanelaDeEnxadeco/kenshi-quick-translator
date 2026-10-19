"""v0.6.0: restaurar original, aviso de backup, revisão (duvidosos, marcadores, desfazer), segunda passada.

Não precisa de .mod real: usa unidades montadas à mão. Roda com o toolkit real ou com o stub só de importação.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kenshi_quick_translator import core
from kenshi_quick_translator.core import Options, install_translation_info, translate_project
from kenshi_quick_translator.project import ATTENTION, AUTO, IGNORED, PENDING, REVIEWED, Project, Unit
from kenshi_quick_translator.providers import Provider
from kenshi_quick_translator.restore import (TRANSLATED_SUFFIX, backup_path, has_backup, installed_mod_path,
                                     restore_original)
from kenshi_quick_translator.review import (UndoHistory, count_doubtful, doubtful_indexes, marker_diff, reason,
                                    source_languages)


def unit(src, tr="", status=PENDING, field="", sid="1", lang=""):
    return Unit(string_id=sid, field=field, source=src, typecode=2, record_name="r", translation=tr, status=status, lang=lang)


class Restore(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.k = Path(self._t.name)
        self.mod = installed_mod_path(self.k, "Test.mod")
        self.mod.parent.mkdir(parents=True)

    def tearDown(self):
        self._t.cleanup()

    def test_sem_backup_nao_restaura(self):
        self.mod.write_bytes(b"traduzido")
        self.assertFalse(has_backup(self.k, "Test.mod"))
        with self.assertRaises(FileNotFoundError):
            restore_original(self.k, "Test.mod")
        self.assertEqual(self.mod.read_bytes(), b"traduzido")  # nada mudou

    def test_restaura_e_guarda_a_traducao(self):
        backup_path(self.k, "Test.mod").write_bytes(b"original")
        self.mod.write_bytes(b"traduzido")
        r = restore_original(self.k, "Test.mod")
        self.assertEqual(self.mod.read_bytes(), b"original")
        self.assertEqual(r.kept_translation, self.mod.with_name("Test.mod" + TRANSLATED_SUFFIX))
        self.assertEqual(r.kept_translation.read_bytes(), b"traduzido")
        self.assertTrue(has_backup(self.k, "Test.mod"))  # o backup continua: dá para traduzir de novo
        self.assertFalse(list(self.mod.parent.glob("*.tmp-restaurar")))

    def test_ja_original_nao_cria_copia(self):
        backup_path(self.k, "Test.mod").write_bytes(b"original")
        self.mod.write_bytes(b"original")
        self.assertIsNone(restore_original(self.k, "Test.mod").kept_translation)

    def test_mod_apagado_volta(self):
        backup_path(self.k, "Test.mod").write_bytes(b"original")
        restore_original(self.k, "Test.mod")
        self.assertEqual(self.mod.read_bytes(), b"original")


class InstallInfoTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.k = self.d / "k"
        (self.k / "data").mkdir(parents=True)
        (self.k / "data" / "mods.cfg").write_text("Test.mod\n")
        self.built = self.d / "Test.mod"
        self.built.write_bytes(b"novo")
        self.dest = installed_mod_path(self.k, "Test.mod")
        self.dest.parent.mkdir(parents=True)

    def tearDown(self):
        self._t.cleanup()

    def test_avisa_quando_o_backup_foi_criado_agora(self):
        self.dest.write_bytes(b"original")
        with mock.patch.object(core, "_is_ours", return_value=False):
            info = install_translation_info(self.k, self.built, "Test.mod")
        self.assertTrue(info.backup_created)
        self.assertEqual(info.backup, backup_path(self.k, "Test.mod"))
        self.assertEqual(info.backup.read_bytes(), b"original")
        self.assertFalse(info.replaced_translation)
        self.assertEqual(self.dest.read_bytes(), b"novo")

    def test_segunda_instalacao_nao_refaz_backup(self):
        self.dest.write_bytes(b"original")
        with mock.patch.object(core, "_is_ours", return_value=False):
            install_translation_info(self.k, self.built, "Test.mod")
        with mock.patch.object(core, "_is_ours", return_value=True):  # agora o que está lá é tradução
            info = install_translation_info(self.k, self.built, "Test.mod")
        self.assertFalse(info.backup_created)
        self.assertTrue(info.replaced_translation)
        self.assertEqual(info.backup.read_bytes(), b"original")  # o original não foi sobrescrito

    def test_tupla_antiga_continua(self):
        dest, changed = core.install_translation(self.k, self.built, "Test.mod")
        self.assertEqual(dest, self.dest)
        self.assertFalse(changed)  # Test.mod já estava no mods.cfg


class Review(unittest.TestCase):
    def test_diff_de_marcadores(self):
        d = marker_diff("Oi /TEAMUP/ e /BROTHER/", "Hi /TEAMUP/ e /GETLOST/")
        self.assertEqual(d.missing, ["/BROTHER/"])
        self.assertEqual(d.extra, ["/GETLOST/"])
        self.assertEqual([ok for _a, _b, ok in d.spans], [True, False])
        s = "Hi /TEAMUP/ e /GETLOST/"
        self.assertEqual(s[d.spans[1][0]:d.spans[1][1]], "/GETLOST/")

    def test_marcador_repetido_a_mais(self):
        d = marker_diff("a /X1/", "b /X1/ /X1/")
        self.assertEqual(d.extra, ["/X1/"])
        self.assertEqual([ok for *_r, ok in d.spans], [True, False])

    def test_traducao_vazia_nao_acusa(self):
        self.assertTrue(marker_diff("a /TEAMUP/", "  ").ok)

    def test_motivos(self):
        self.assertEqual(reason(unit("Hello there", "", ATTENTION)), "atencao")
        self.assertEqual(reason(unit("Go /TEAMUP/ now", "Vá agora", AUTO)), "marcadores")
        self.assertEqual(reason(unit("Hello there", "Hello there", AUTO)), "igual")
        self.assertEqual(reason(unit("Hello there", "Olá", AUTO)), "")
        self.assertEqual(reason(unit("OK", "OK", AUTO)), "")  # curto demais para acusar
        self.assertEqual(reason(unit("Hello there", "", IGNORED)), "")
        self.assertEqual(reason(unit("Hello there", "Hello there", REVIEWED)), "")  # a pessoa decidiu

    def test_contador(self):
        us = [unit("Hello there", "", ATTENTION), unit("Go /TEAMUP/ now", "Vá", AUTO),
              unit("Same words", "Same words", AUTO), unit("Fine text", "Texto", AUTO)]
        d = count_doubtful(us)
        self.assertEqual((d.attention, d.broken_markers, d.same_as_source, d.total), (1, 1, 1, 3))
        self.assertEqual(doubtful_indexes(us), [0, 1, 2])

    def test_desfazer(self):
        h = UndoHistory()
        a, b = unit("one", "um", AUTO, sid="1"), unit("two", "dois", AUTO, sid="2")
        h.push(a)
        a.translation, a.status = "UM", REVIEWED
        h.push(b)
        b.translation, b.status = "DOIS", REVIEWED
        self.assertEqual(len(h), 2)
        self.assertEqual(h.pop([a, b]), 1)
        self.assertEqual((b.translation, b.status), ("dois", AUTO))
        self.assertEqual(h.pop([a, b]), 0)
        self.assertEqual((a.translation, a.status), ("um", AUTO))
        self.assertIsNone(h.pop([a, b]))

    def test_desfazer_ignora_texto_que_nao_existe_mais(self):
        h = UndoHistory()
        gone = unit("x", "y", AUTO, sid="9")
        h.push(gone)
        self.assertIsNone(h.pop([unit("a", "b", AUTO)]))

    def test_limite_da_pilha(self):
        h = UndoHistory(limit=3)
        for i in range(10):
            h.push(unit("s", str(i), AUTO, sid=str(i)))
        self.assertEqual(len(h), 3)

    def test_idiomas_de_origem(self):
        us = [unit("a", lang="en"), unit("b", lang="en"), unit("c", lang="zh"), unit("d")]
        self.assertEqual(source_languages(us), {"en": 2, "zh": 1})


class Tagged(Provider):
    name, label = "tag", "Tag"

    def __init__(self, prefix):
        self.prefix, self.calls = prefix, []

    def translate_batch(self, texts, source, target):
        self.calls += texts
        return [f"{self.prefix}{t}" for t in texts]


class SecondPass(unittest.TestCase):
    def make(self, tmp):
        p = Project(mod_name="T.mod", mod_sha1="x", units=[
            unit("Hello world", "parcial", ATTENTION, sid="1"),
            unit("Good morning", "", ATTENTION, sid="2"),
            unit("Fresh text", "", PENDING, sid="3"),
            unit("Reviewed one", "feito", REVIEWED, sid="4"),
        ])
        p.path = Path(tmp) / "p.json"
        return p

    def test_so_refaz_os_conferir(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, prov = self.make(tmp), Tagged("PT:")
            rep = translate_project(p, prov, options=Options(only_attention=True, workers=1))
            self.assertEqual(sorted(prov.calls), ["Good morning", "Hello world"])
            self.assertEqual(p.units[0].status, AUTO)
            self.assertTrue(p.units[0].translation.startswith("PT:"))
            self.assertEqual(p.units[2].status, PENDING)  # pendente não é tocado
            self.assertEqual((p.units[3].translation, p.units[3].status), ("feito", REVIEWED))
            self.assertEqual(rep.translated, 2)

    def test_nao_piora_o_que_ja_havia(self):
        class Ruin(Provider):
            name, label = "ruin", "Ruin"
            def translate_batch(self, texts, source, target):
                return ["" for _ in texts]  # perde a ficha → marcador estragado → atenção de novo
        with tempfile.TemporaryDirectory() as tmp:
            p = self.make(tmp)
            p.units[0] = unit("Hello /TEAMUP/ world", "parcial /TEAMUP/", ATTENTION, sid="1")
            translate_project(p, Ruin(), options=Options(only_attention=True, workers=1))
            self.assertEqual(p.units[0].translation, "parcial /TEAMUP/")
            self.assertEqual(p.units[0].status, ATTENTION)

    def test_opcao_normal_nao_muda(self):
        self.assertFalse(Options().only_attention)
        with tempfile.TemporaryDirectory() as tmp:
            p, prov = self.make(tmp), Tagged("PT:")
            translate_project(p, prov, options=Options(workers=1))
            self.assertEqual(prov.calls, ["Fresh text"])  # comportamento antigo: só pendentes


if __name__ == "__main__":
    unittest.main()


class Textos(unittest.TestCase):
    def test_textos_novos_tem_5_idiomas(self):
        from kenshi_quick_translator.i18n_v06 import MORE_V06, PATTERNS_V06
        for row in MORE_V06 + PATTERNS_V06:
            self.assertEqual(len(row), 5, row[0])
            self.assertTrue(all(c.strip() for c in row), row[0])

    def test_traducao_dos_botoes(self):
        import sys
        try:
            import tkinter  # noqa: F401
        except ImportError:
            for m in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk", "tkinter.font"):
                sys.modules[m] = mock.MagicMock()
        from kenshi_quick_translator import i18n
        try:
            i18n.set_language("en")
            self.assertEqual(i18n.tr("Restaurar o original"), "Restore the original")
            self.assertEqual(i18n.tr("Duvidosos"), "Doubtful")
            self.assertEqual(i18n.tr(" | ⚠ 7 duvidosos"), " | ⚠ 7 doubtful")
            i18n.set_language("zh")
            self.assertEqual(i18n.tr("Fechar"), "关闭")
        finally:
            i18n.set_language("pt")

    def test_aviso_de_instalacao(self):
        import sys
        try:
            import tkinter  # noqa: F401
        except ImportError:
            for m in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk", "tkinter.font"):
                sys.modules[m] = mock.MagicMock()
        from kenshi_quick_translator.core import InstallInfo
        from kenshi_quick_translator.ui_actions import install_notice
        bk = Path("/k/mods/T/T.mod.original")
        self.assertIn("foi guardado", install_notice(InstallInfo(Path("x"), False, bk, True), "T.mod"))
        self.assertIn("continua guardado", install_notice(InstallInfo(Path("x"), False, bk, False), "T.mod"))
        self.assertEqual(install_notice(InstallInfo(Path("x"), False), "T.mod"), "")  # modo dependente: sem aviso
        self.assertIn(str(bk), install_notice(InstallInfo(Path("x"), False, bk, True), "T.mod"))


class SessionLevel(unittest.TestCase):
    def setUp(self):
        from kenshi_quick_translator.config import Config
        from kenshi_quick_translator.session import Session
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        self.s = Session(Config(), workdir=self.tmp)
        self.s.project = Project(mod_name="T.mod", mod_sha1="x", units=[
            unit("Hello there", "Olá", AUTO, sid="1", lang="en"),
            unit("Go /TEAMUP/ now", "Vá agora", AUTO, sid="2", lang="en"),
            unit("你好吗", "", PENDING, sid="3", lang="zh"),
            unit("Same words", "Same words", AUTO, sid="4", lang="en"),
        ])
        self.s.project.path = self.tmp / "p.json"
        self.s.mod_path = self.tmp / "T.mod"

    def tearDown(self):
        self.s.close()
        self._t.cleanup()

    def test_filtro_duvidosos_e_idioma(self):
        self.assertEqual([i for i, _ in self.s.visible_units("duvidosa")], [1, 3])
        self.assertEqual([i for i, _ in self.s.visible_units("todos", "", "zh")], [2])
        self.assertEqual([i for i, _ in self.s.visible_units("duvidosa", "", "en")], [1, 3])
        self.assertEqual(self.s.source_language_counts(), {"en": 3, "zh": 1})
        self.assertEqual(self.s.doubtful().total, 2)

    def test_editar_e_desfazer(self):
        self.s.edit(0, "Oi")
        self.assertEqual((self.s.project.units[0].translation, self.s.project.units[0].status), ("Oi", REVIEWED))
        self.assertEqual(self.s.undo_edit(), 0)
        self.assertEqual((self.s.project.units[0].translation, self.s.project.units[0].status), ("Olá", AUTO))
        self.assertIsNone(self.s.undo_edit())

    def test_edicao_recusada_nao_entra_no_desfazer(self):
        with self.assertRaises(ValueError):
            self.s.edit(1, "Vá agora sem marcador")  # falta /TEAMUP/
        self.assertEqual(len(self.s.undo), 0)

    def test_abrir_outro_mod_limpa_o_desfazer(self):
        self.s.edit(0, "Oi")
        self.s.undo.clear()  # open_mod faz isso; aqui só confirmamos a API
        self.assertIsNone(self.s.undo_edit())


class FakeText:
    """Imita o pedaço de tk.Text usado para colorir: guarda onde cada marca foi posta."""

    def __init__(self):
        self.marks = {}

    def tag_remove(self, tag, *_a):
        self.marks[tag] = []

    def tag_add(self, tag, a, b):
        self.marks.setdefault(tag, []).append((a, b))


class Highlight(unittest.TestCase):
    def test_cores_dos_marcadores(self):
        import sys
        try:
            import tkinter  # noqa: F401
        except ImportError:
            for m in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk", "tkinter.font"):
                sys.modules[m] = mock.MagicMock()
        from kenshi_quick_translator.ui_actions import ActionsMixin
        obj = ActionsMixin()
        obj.src_text, obj.dst_text = FakeText(), FakeText()
        src = "Go /TEAMUP/ and /BROTHER/"
        obj.highlight_markers(src, "Vá /TEAMUP/ e /GETLOST/")
        # original: TEAMUP presente (verde), BROTHER sumiu (vermelho)
        self.assertEqual(obj.src_text.marks["mok"], [("1.0+3c", "1.0+11c")])
        self.assertEqual(obj.src_text.marks["mbad"], [("1.0+16c", "1.0+25c")])
        # tradução: TEAMUP verde, GETLOST (sobrando) vermelho
        self.assertEqual(obj.dst_text.marks["mok"], [("1.0+3c", "1.0+11c")])
        self.assertEqual(len(obj.dst_text.marks["mbad"]), 1)
        obj.highlight_markers(src, "")  # tradução vazia: nada é acusado, tudo do original fica "ok"
        self.assertEqual(obj.src_text.marks["mbad"], [])
        self.assertEqual(len(obj.src_text.marks["mok"]), 2)
