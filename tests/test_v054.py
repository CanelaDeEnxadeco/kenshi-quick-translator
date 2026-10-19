"""v0.5.4: mods de mesmo nome não dividem progresso; detalhe de status dos serviços; filtros da lista."""
import json
import tempfile
import unittest
from pathlib import Path

from kenshi_quick_translator.project import Project, _norm, project_path, resolve_project_path
from tests.test_aggregate import Fake, agg


class MesmoNomeTests(unittest.TestCase):
    def test_dois_mods_com_o_mesmo_nome_tem_projetos_separados(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d) / "proj"
            a = Path(d) / "workshop" / "Auto factory.mod"
            b = Path(d) / "mods" / "Auto factory.mod"
            pa = resolve_project_path(w, a, "pt-BR")
            self.assertEqual(pa, project_path(w, "Auto factory.mod", "pt-BR"))
            Project(mod_name=a.name, mod_sha1="x", mod_path=_norm(a)).save(pa)
            pb = resolve_project_path(w, b, "pt-BR")
            self.assertNotEqual(pa, pb)
            self.assertIn("~", pb.name)
            Project(mod_name=b.name, mod_sha1="y", mod_path=_norm(b)).save(pb)
            self.assertEqual(resolve_project_path(w, a, "pt-BR"), pa)
            self.assertEqual(resolve_project_path(w, b, "pt-BR"), pb)

    def test_projeto_antigo_sem_dono_continua_valendo(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            legacy = project_path(w, "M.mod", "pt-BR")
            legacy.write_text(json.dumps({"mod_name": "M.mod", "units": []}), encoding="utf-8")
            self.assertEqual(resolve_project_path(w, Path(d) / "x" / "M.mod", "pt-BR"), legacy)


class StatusDetalheTests(unittest.TestCase):
    def test_motivo_e_falhas_seguidas(self):
        g, b = Fake("Google", 429), Fake("Bing")
        a, clock, _ = agg([g, b])
        a.translate_batch(["a"], "en", "pt-BR")
        d = {x["name"]: x for x in a.status_detail()}
        self.assertGreater(d["Google"]["wait"], 0)
        self.assertEqual(d["Google"]["strikes"], 1)
        self.assertTrue(d["Google"]["why"])
        self.assertEqual(d["Bing"]["wait"], 0)
        clock.t += 61
        g.fail_status = None
        a.translate_batch(["c"], "en", "pt-BR")
        self.assertEqual({x["name"]: x for x in a.status_detail()}["Google"]["why"], "")


if __name__ == "__main__":
    unittest.main()
