import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kenshi_quick_translator import consistency
from kenshi_quick_translator.glossary import Glossary
from kenshi_quick_translator.memory import TranslationMemory
from kenshi_quick_translator.project import ATTENTION, AUTO, PENDING, Unit


def U(src, tr, st=AUTO):
    return Unit(string_id="1-x", field="f", source=src, typecode=0, record_name="n", translation=tr, status=st)


class Consistencia(unittest.TestCase):
    def test_divergente_e_unificar(self):
        us = [U("Hello", "Olá"), U("Hello", "Oi"), U("Hello", "Olá"), U("Bye", "Tchau")]
        rep = consistency.check(us)
        self.assertEqual(len(rep.divergences), 1)
        self.assertEqual(rep.divergences[0].best, "Olá")
        self.assertEqual(consistency.unify(us, rep.divergences[0]), 1)
        self.assertEqual(consistency.check(us).total, 0)

    def test_pendente_nao_conta(self):
        self.assertEqual(consistency.check([U("A", "x"), U("A", "", PENDING)]).total, 0)

    def test_glossario(self):
        g = Glossary({"Holy Nation": "Nação Sagrada"})
        us = [U("The Holy Nation rules.", "A Nação Santa governa."), U("Holy Nation", "Nação Sagrada")]
        rep = consistency.check(us, g)
        self.assertEqual([m.index for m in rep.misses], [0])
        self.assertEqual(consistency.mark_for_review(us, rep.misses), 1)
        self.assertEqual(us[0].status, ATTENTION)


class UsoGlossario(unittest.TestCase):
    def test_conta(self):
        g = Glossary({"Holy Nation": "Nação Sagrada"})
        us = [U("Holy Nation", "Nação Sagrada"), U("The Holy Nation", "A Nação Santa"), U("Other", "Outro")]
        self.assertEqual(consistency.glossary_usage(us, g), (1, 1))
        self.assertEqual(consistency.glossary_usage(us, None), (0, 0))


class LogDeErros(unittest.TestCase):
    def test_grava_e_gira(self):
        from kenshi_quick_translator import errorreport as er
        d = Path(tempfile.mkdtemp()) / "x" / "erros.log"
        er.log_error("Traceback: boom", d)
        self.assertIn("boom", d.read_text(encoding="utf-8"))
        old = er.MAX_LOG; er.MAX_LOG = 10
        try:
            er.log_error("segundo", d)
        finally:
            er.MAX_LOG = old
        self.assertTrue(d.with_suffix(".antigo").exists())
        self.assertIn("segundo", d.read_text(encoding="utf-8"))

    def test_log_nunca_levanta_erro(self):
        from kenshi_quick_translator import errorreport as er
        er.log_error("x", Path("/proc/nao/existe/erros.log"))


class TraducoesNovas(unittest.TestCase):
    def test_textos_com_numero_e_nome(self):
        import types
        from unittest import mock
        try:
            import tkinter  # noqa: F401
        except Exception:  # noqa: BLE001
            for n in ("tkinter", "tkinter.ttk", "tkinter.font", "tkinter.filedialog", "tkinter.messagebox"):
                sys.modules[n] = mock.MagicMock()
        from kenshi_quick_translator import i18n
        try:
            i18n.set_language("en")
            self.assertEqual(i18n.tr("Español: 12 termos"), "Español: 12 terms")
            self.assertIn("12 phrases exported", i18n.tr("12 frases exportadas."))
            i18n.set_language("es")
            self.assertEqual(i18n.tr("Português (Brasil): vazio"), "Português (Brasil): vacío")
            i18n.set_language("zh")
            self.assertEqual(i18n.tr("Exportar"), "导出")
        finally:
            i18n.set_language("pt")


class MemoriaArquivo(unittest.TestCase):
    def test_exportar_importar(self):
        d = Path(tempfile.mkdtemp())
        a = TranslationMemory(d / "a.sqlite"); a.put("Hi", "pt-BR", "Oi"); a.put("Yo", "es", "Hola")
        self.assertEqual(a.export_json(d / "m.json"), 2)
        b = TranslationMemory(d / "b.sqlite"); b.put("Hi", "pt-BR", "Olá")
        self.assertEqual(b.import_json(d / "m.json"), 1)  # "Hi" já existe e fica
        self.assertEqual(b.get("Hi", "pt-BR"), "Olá")
        self.assertEqual(b.get("Yo", "es"), "Hola")
        self.assertEqual(b.import_json(d / "m.json", overwrite=True), 2)
        self.assertEqual(b.get("Hi", "pt-BR"), "Oi")
        a.close(); b.close()


if __name__ == "__main__":
    unittest.main()
