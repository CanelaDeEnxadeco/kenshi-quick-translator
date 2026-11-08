import unittest
from types import SimpleNamespace as U

from kenshi_quick_translator import fontcheck, suggest
from kenshi_quick_translator.project import Project, Unit, ATTENTION, PENDING, REVIEWED
from kenshi_quick_translator.errorreport import build_report


class SuggestTest(unittest.TestCase):
    def test_sugere_preset_usado(self):
        presets = {"c": {"nome": "Cidades", "terms": {"Black Desert City": "Cidade do Deserto Negro", "Squin": None}},
                   "f": {"nome": "Facções", "terms": {"Holy Nation": "Nação Sagrada"}}}
        src = ["Go to Black Desert City.", "Black Desert City is far", "Black Desert City!", "Hello"]
        r = suggest.suggest_presets(src, presets)
        self.assertEqual([x["id"] for x in r], ["c"])
        self.assertEqual(r[0]["hits"], 3)

    def test_palavra_inteira(self):
        presets = {"c": {"nome": "C", "terms": {"Squin": None}}}
        self.assertEqual(suggest.suggest_presets(["Squinting Squinting Squinting"], presets), [])

    def test_nomes_novos(self):
        us = [U(field="", source="Kaelor"), U(field="", source="Hamut"), U(field="name", source="Zed"),
              U(field="", source="the thing"), U(field="", source="Old Guard Camp")]
        self.assertEqual(suggest.new_names(us, ["Hamut"]), ["Kaelor", "Old Guard Camp"])


class FontTest(unittest.TestCase):
    def test_acentos_ok_e_aspas_curvas_nao(self):
        us = [U(string_id="a", field="", translation="Ação não é “fácil” — né…"), U(string_id="b", field="", translation="ok ç ã é")]
        r = fontcheck.scan(us)
        self.assertEqual([x[0] for x in r["units"]], ["a"])
        n, left = fontcheck.fix_typography(us)
        self.assertEqual(n, 1)
        self.assertEqual(us[0].translation, 'Ação não é "fácil" - né...')
        self.assertFalse(left)
        self.assertEqual(fontcheck.scan(us)["units"], [])

    def test_xml(self):
        xml = '<Codes><Code range="32 255"/></Codes><Codes><Code range="32 127"/></Codes>'
        self.assertEqual(fontcheck.parse_ranges(xml), ((32, 127),))
        self.assertEqual(fontcheck.parse_ranges(""), fontcheck.DEFAULT_RANGES)

    def test_sem_solucao(self):
        us = [U(string_id="a", field="", translation="日本")]
        n, left = fontcheck.fix_typography(us)
        self.assertEqual(n, 0)
        self.assertEqual(sum(left.values()), 2)


class UpdateTest(unittest.TestCase):
    def _proj(self, sha, units):
        return Project(mod_name="m.mod", mod_sha1=sha, units=units)

    def test_merge_e_pendentes(self):
        old = self._proj("a", [Unit("1", "t", "Hello", 1, "r", translation="Olá", status=REVIEWED),
                               Unit("2", "t", "Bye", 1, "r", translation="Tchau", status="automatica"),
                               Unit("3", "t", "Gone", 1, "r")])
        new = self._proj("b", [Unit("1", "t", "Hello", 1, "r"), Unit("2", "t", "Goodbye", 1, "r"), Unit("4", "t", "New", 1, "r")])
        new._merge(old)
        self.assertEqual(new.update_info, {"antigos": 3, "novos": 1, "mudaram": 1, "removidos": 1, "mod_mudou": True})
        self.assertEqual(new.units[0].translation, "Olá")
        self.assertEqual(new.units[1].status, ATTENTION)
        self.assertEqual(new.mark_changed_pending(), 1)
        self.assertEqual(new.units[1].status, PENDING)
        self.assertEqual(new.units[0].status, REVIEWED)


class ReportTest(unittest.TestCase):
    def test_relatorio(self):
        r = build_report("0.7.1", {"Mod": "x.mod", "Chave": ""}, "Traceback...")
        self.assertIn("0.7.1", r); self.assertIn("Mod: x.mod", r); self.assertNotIn("Chave", r); self.assertIn("Traceback", r)


if __name__ == "__main__":
    unittest.main()
