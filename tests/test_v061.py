import tempfile
import unittest
from pathlib import Path

from kenshi_quick_translator import cleanup, i18n


def _make(root: Path) -> None:
    (root / "projetos" / "backup").mkdir(parents=True)
    (root / "projetos" / "A.pt-BR.ktproj.json").write_text("{}")
    (root / "projetos" / "B.pt-BR.ktproj.json").write_text("{}")
    (root / "projetos" / "backup" / "A.1.bak").write_text("x")
    (root / "memoria.sqlite").write_bytes(b"db")
    (root / "idiomas.json").write_text("{}")
    (root / "glossario.json").write_text("{}")
    (root / "config.json").write_text("{}")
    (root / "translator_blacklist.txt").write_text("bone name")


class Limpeza(unittest.TestCase):
    def test_scan_conta(self):
        with tempfile.TemporaryDirectory() as t:
            _make(Path(t))
            got = {i.key: i.files for i in cleanup.scan(t)}
            self.assertEqual(got["projetos"], 2)
            self.assertEqual(got["backup"], 1)
            self.assertEqual(got["memoria"], 1)

    def test_apaga_so_o_marcado(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            _make(r)
            res = cleanup.clean(r, ["projetos", "backup"])
            self.assertEqual(res.removed, {"projetos": 2, "backup": 1})
            self.assertFalse(list((r / "projetos").glob("*.json")))
            self.assertFalse((r / "projetos" / "backup").exists())
            for keep in ("memoria.sqlite", "idiomas.json", "glossario.json", "config.json", "translator_blacklist.txt"):
                self.assertTrue((r / keep).exists(), keep)

    def test_nao_toca_listas_do_usuario_e_ignora_chave_invalida(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            _make(r)
            cleanup.clean(r, ["memoria", "idiomas", "glossario", "config", "../x", "tudo"])
            self.assertTrue((r / "translator_blacklist.txt").exists())
            self.assertTrue((r / "projetos" / "A.pt-BR.ktproj.json").exists())
            self.assertFalse((r / "memoria.sqlite").exists())

    def test_pasta_vazia_nao_quebra(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(sum(i.files for i in cleanup.scan(t)), 0)
            self.assertEqual(cleanup.clean(t, ["projetos", "memoria"]).total, 0)

    def test_traducoes_nos_5_idiomas(self):
        texts = [lbl for _k, lbl, note in cleanup.CATEGORIES for lbl in (lbl, note)]
        texts += ["Limpar dados…", "Apagar", "Nada marcado.", "Não deu para apagar:"]
        old = i18n.current() if hasattr(i18n, "current") else "pt"
        try:
            for lang in ("en", "es", "ru", "zh"):
                i18n.set_language(lang)
                for tx in texts:
                    if tx in ("Glossário",) or (lang == "es" and tx == "Nada marcado."):
                        continue
                    self.assertNotEqual(i18n.tr(tx), tx, (lang, tx))
            i18n.set_language("en")
            self.assertEqual(i18n.tr("3 arquivo(s) apagado(s)."), "3 file(s) deleted.")
        finally:
            i18n.set_language(old if isinstance(old, str) else "pt")


if __name__ == "__main__":
    unittest.main()
