"""Testes da versão 0.5.1 (zerar progresso, cópia de segurança, mensagens, pt-BR)."""

import json
import tempfile
import unittest
from pathlib import Path

from kenshi_quick_translator.config import Config
from kenshi_quick_translator.providers import friendly_error
from kenshi_quick_translator.session import Session


class V051(unittest.TestCase):
    def test_friendly_429(self):
        msg = "Google falhou 3 vezes: Erro HTTP 429. <!DOCTYPE html><html>...</html>"
        out = friendly_error(msg)
        self.assertIn("429", out)
        self.assertNotIn("<html", out.lower())

    def test_old_pt_becomes_ptbr(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            p.write_text(json.dumps({"target_lang": "pt"}), encoding="utf-8")
            self.assertEqual(Config.load(p).target_lang, "pt-BR")
            cfg = Config.load(p)
            cfg.target_lang = "pt"  # escolha consciente depois da correção
            cfg.save(p)
            self.assertEqual(Config.load(p).target_lang, "pt")

    def test_reset_makes_backup(self):
        with tempfile.TemporaryDirectory() as d:
            s = Session(workdir=Path(d))
            pf = s.projects_folder
            pf.mkdir(parents=True, exist_ok=True)
            from kenshi_quick_translator.project import project_path
            p = project_path(pf, "x.mod", s.cfg.target_lang)
            p.write_text("{}", encoding="utf-8")
            self.assertTrue(s.reset_progress("x.mod"))
            self.assertFalse(p.exists())
            self.assertEqual(len(list((pf / "backup").glob("*.bak"))), 1)
            self.assertFalse(s.reset_progress("x.mod"))


if __name__ == "__main__":
    unittest.main()


class IdiomasInterface(unittest.TestCase):
    def test_russo_e_chines_alinhados(self):
        from kenshi_quick_translator import i18n
        from kenshi_quick_translator.i18n_extra import RU_ZH
        self.assertEqual(len(RU_ZH), len(i18n.ROWS))
        for row, (ru, zh) in zip(i18n.ROWS, RU_ZH):
            for t in (ru, zh):
                self.assertTrue(t.strip(), row[0])
                self.assertEqual(row[0].count("\n"), t.count("\n"), row[0])
                if t is ru:  # em chinês o espaço final não é necessário
                    self.assertEqual(row[0].endswith(" "), t.endswith(" "), row[0])
        i18n.set_language("ru")
        self.assertEqual(i18n.tr("Traduzir para:"), "Перевести на:")
        i18n.set_language("zh")
        self.assertEqual(i18n.tr("Traduzir para:"), "翻译为:")
        i18n.set_language("pt")


class TraducaoCompleta(unittest.TestCase):
    def test_tabelas_extras_completas(self):
        from kenshi_quick_translator.i18n_more import MORE, PATTERNS
        for row in MORE:
            self.assertEqual(len(row), 5, row[0])
            for t in row[1:]:
                self.assertTrue(t.strip(), row[0])
                self.assertEqual(row[0].count("\n"), t.count("\n"), row[0])
        for p in PATTERNS:
            self.assertEqual(len(p), 5)

    def test_nomes_usados_como_chave_nao_mudam(self):
        """Idiomas, serviços e tipos são reconhecidos pelo texto: traduzir quebraria a seleção."""
        from kenshi_quick_translator import i18n
        from kenshi_quick_translator.providers import LANGUAGES, SPECS
        from kenshi_quick_translator.services import KINDS
        try:
            for lang in ("en", "es", "ru", "zh"):
                i18n.set_language(lang)
                for code, name in LANGUAGES.items():
                    shown = f"{name} ({code})" if code != "auto" else name
                    self.assertEqual(i18n.tr(shown), shown, (lang, shown))
                for spec in SPECS:
                    self.assertEqual(i18n.tr(spec.label), spec.label, (lang, spec.label))
                for label in KINDS.values():
                    self.assertEqual(i18n.tr(label), label, (lang, label))
        finally:
            i18n.set_language("pt")

    def test_numeros_e_nomes(self):
        from kenshi_quick_translator import i18n
        try:
            i18n.set_language("en")
            self.assertEqual(i18n.tr("18 mods"), "18 mods")
            self.assertEqual(i18n.tr("3 de 18"), "3 of 18")
            self.assertEqual(i18n.names("Inglês + Japonês"), "English + Japanese")
            i18n.set_language("zh")
            self.assertEqual(i18n.tr("18 mods"), "18 个模组")
            self.assertEqual(i18n.tr("Mod 2 de 5: x"), "模组 2/5: x")
        finally:
            i18n.set_language("pt")
