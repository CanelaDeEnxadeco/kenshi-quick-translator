"""Presets de glossário com os nomes oficiais do Kenshi."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_quick_translator.glossary import Glossary, list_presets, load_preset


class PresetsTest(unittest.TestCase):
    def test_lista_tres_presets_com_termos(self):
        ps = [p for p in list_presets() if p['idioma'] == 'pt-BR']
        ids = {p["id"] for p in ps}
        base = {"cidades", "faccoes", "personagens", "racas", "armas", "armaduras", "itens", "livros", "construcoes", "pesquisas", "regioes", "personagens_todos", "comida", "cenarios"}
        self.assertEqual(ids, {"vanilla_pt-BR_" + n for n in base})
        for p in ps:
            self.assertGreater(p["total"], 10)
            self.assertEqual(p["idioma"], "pt-BR")

    def test_termos_conhecidos(self):
        f = load_preset("vanilla_pt-BR_faccoes")
        self.assertEqual(f["Shek Kingdom"], "Reino Shek")
        self.assertEqual(f["United Cities"], "União das Cidades")
        self.assertEqual(f["Holy Nation"], "Nação Sagrada")  # sem o "The"
        c = load_preset("vanilla_pt-BR_cidades")
        self.assertIsNone(c["Squin"])  # nome igual no jogo: fica sem traduzir
        p = load_preset("vanilla_pt-BR_personagens")
        self.assertEqual(p["Lord Inaba"], "Lorde Inaba")
        self.assertIsNone(p["Hamut"])

    def test_presets_por_idioma(self):
        from kenshi_quick_translator.glossary import presets_for
        for code in ("pt-BR", "es", "fr", "de", "ru", "ja", "ko", "zh"):
            ps, oficial = presets_for(code)
            self.assertTrue(oficial, code)
            self.assertTrue(ps and all(p["idioma"] == code for p in ps), code)
        for code in ("it", "uk", "pl", "tr", "pt", "en"):
            ps, oficial = presets_for(code)
            self.assertFalse(oficial, code)
            self.assertEqual([p["idioma"] for p in ps], ["*"], code)
        self.assertEqual(load_preset("vanilla_neutro_manter_nomes")["Lord Inaba"], None) if "Lord Inaba" in load_preset("vanilla_neutro_manter_nomes") else None

    def test_todos_os_presets_sem_lixo(self):
        for p in list_presets():
            for term, tr in load_preset(p["id"]).items():
                for x in (term, tr or ""):
                    self.assertNotIn("/", x, p["id"])
                    self.assertNotIn("override", x.lower(), p["id"])
                self.assertFalse(term[:1].islower(), (p["id"], term))

    def test_sem_lixo_interno(self):
        for pid in ("vanilla_pt-BR_cidades", "vanilla_pt-BR_faccoes", "vanilla_pt-BR_personagens"):
            for term, tr in load_preset(pid).items():
                for s in (term, tr or ""):
                    self.assertNotIn("/", s)
                    self.assertNotIn("override", s.lower())
                    self.assertNotIn("(", s)
                self.assertFalse(term[:1].islower(), term)

    def test_merge_nao_apaga_edicoes_do_usuario(self):
        g = Glossary(terms={"Shek Kingdom": "Reino dos Shek"})
        added, updated, skipped = g.merge(load_preset("vanilla_pt-BR_faccoes"))
        self.assertEqual(g.terms["Shek Kingdom"], "Reino dos Shek")
        self.assertGreater(added, 50)
        self.assertEqual(updated, 0)
        self.assertGreaterEqual(skipped, 1)
        added, updated, skipped = g.merge(load_preset("vanilla_pt-BR_faccoes"), overwrite=True)
        self.assertEqual(g.terms["Shek Kingdom"], "Reino Shek")
        self.assertEqual(updated, 1)

    def test_glossario_com_preset_acha_os_termos_no_texto(self):
        g = Glossary()
        g.merge(load_preset("vanilla_pt-BR_faccoes"))
        g.merge(load_preset("vanilla_pt-BR_personagens"))
        found = g.find("Lord Inaba leads the Shek Kingdom and Hamut watches.")
        self.assertEqual([f[2] for f in found], ["Lorde Inaba", "Reino Shek", "Hamut"])

    def test_id_invalido(self):
        with self.assertRaises(ValueError):
            load_preset("../config")


if __name__ == "__main__":
    unittest.main()
