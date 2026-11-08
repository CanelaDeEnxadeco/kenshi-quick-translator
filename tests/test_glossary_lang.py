"""Um glossário por idioma de destino: não mistura português com espanhol, e oferece os presets do idioma."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_quick_translator import cleanup
from kenshi_quick_translator.config import Config, glossary_filename
from kenshi_quick_translator.glossary import Glossary, default_preset_ids
from kenshi_quick_translator.session import Session


def make(lang, work):
    return Session(Config(target_lang=lang), workdir=Path(work))


class GlossarioPorIdiomaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nomes_de_arquivo(self):
        self.assertEqual(glossary_filename("pt-BR"), "glossario.json")  # quem já usava o programa mantém o arquivo
        self.assertEqual(glossary_filename("es"), "glossario.es.json")
        self.assertEqual(glossary_filename("../x/y"), "glossario.___x_y.json")

    def test_espanhol_nao_herda_termos_em_portugues(self):
        s = make("es", self.work)
        self.assertEqual(s.glossary.terms, {})
        self.assertEqual(s.glossary.lang, "es")
        pt = make("pt-BR", self.work)
        self.assertIn("Holy Nation", pt.glossary.terms)  # o padrão em português continua valendo para português

    def test_oferta_com_nomes_oficiais_e_aceitar(self):
        s = make("es", self.work)
        offer = s.glossary_offer()
        self.assertTrue(offer["official"])
        self.assertTrue(all(i.startswith("vanilla_es_") for i in offer["ids"]))
        self.assertEqual(len(offer["ids"]), 3)
        n = s.accept_glossary_offer()
        self.assertGreater(n, 100)
        self.assertTrue((self.work / "glossario.es.json").is_file())
        self.assertIsNone(s.glossary_offer())  # a oferta não volta
        data = json.loads((self.work / "glossario.es.json").read_text(encoding="utf-8"))
        self.assertEqual(data["idioma"], "es")
        self.assertFalse((self.work / "glossario.json").exists())  # o de português não foi tocado nem criado

    def test_idioma_sem_traducao_oficial_oferece_manter_nomes(self):
        s = make("it", self.work)
        offer = s.glossary_offer()
        self.assertFalse(offer["official"])
        self.assertGreater(offer["total"], 100)
        s.accept_glossary_offer()
        self.assertTrue(all(v is None for v in s.glossary.terms.values()))

    def test_traduzir_sem_glossario_nao_pergunta_de_novo(self):
        s = make("fr", self.work)
        self.assertIsNotNone(s.glossary_offer())
        s.decline_glossary_offer()
        self.assertIsNone(s.glossary_offer())
        self.assertEqual(s.glossary.terms, {})

    def test_portugues_brasil_nao_recebe_oferta(self):
        self.assertIsNone(make("pt-BR", self.work).glossary_offer())

    def test_arquivo_antigo_sem_idioma_vale_para_portugues(self):
        (self.work / "glossario.json").write_text(json.dumps({"case_sensitive": True, "terms": {"Hub": None}}), encoding="utf-8")
        s = make("pt-BR", self.work)
        self.assertEqual(s.glossary.lang, "pt-BR")
        self.assertEqual(s.glossary.terms, {"Hub": None})
        s.glossary.save(s.glossary_file)
        self.assertEqual(json.loads((self.work / "glossario.json").read_text(encoding="utf-8"))["idioma"], "pt-BR")

    def test_trocar_idioma_troca_o_glossario(self):
        s = make("pt-BR", self.work)
        s.glossary.set("Meu Termo", "Meu Termo PT")
        s.glossary.save(s.glossary_file)
        s.cfg.target_lang = "es"
        s.reload_glossary()
        self.assertNotIn("Meu Termo", s.glossary.terms)
        self.assertEqual([c for c, _n in s.other_glossaries()], ["pt-BR"])
        s.cfg.target_lang = "pt-BR"
        s.reload_glossary()
        self.assertEqual(s.glossary.terms["Meu Termo"], "Meu Termo PT")

    def test_presets_padrao_so_nomes_proprios(self):
        for lang in ("pt-BR", "es", "de", "ja"):
            ids = default_preset_ids(lang)
            self.assertEqual(len(ids), 3, lang)
            self.assertTrue(all(i.endswith(("_cidades", "_faccoes", "_personagens")) for i in ids))

    def test_limpeza_apaga_todos_os_glossarios(self):
        for n in ("glossario.json", "glossario.es.json"):
            (self.work / n).write_text("{}", encoding="utf-8")
        files = [p.name for p in cleanup._paths(self.work, "glossario")]
        self.assertEqual(sorted(files), ["glossario.es.json", "glossario.json"])


if __name__ == "__main__":
    unittest.main()
