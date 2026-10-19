"""v0.5.6: todos os campos de texto, menos a lista do original e o que parece código."""
import tempfile
import unittest
from pathlib import Path

from kenshi_translator_toolkit import FileType, ModFile, RawRecord, TypeCode, dump, load

from kenshi_quick_translator.core import build_translation, translate_project, verify_output
from kenshi_quick_translator.fields import (
    BLACKLIST_FILE,
    DEFAULT_BLACKLIST,
    FieldRules,
    collect_units,
    technical_reason,
)
from kenshi_quick_translator.project import Project
from kenshi_quick_translator.providers import Simulated


def rec(i, typecode, name, strings, flags=0):
    return RawRecord(
        instance_count=0, typecode=typecode, record_id=0, name=name,
        string_id=f"{i}-Test.mod", flags=flags, strings=strings,
    )


def make_mod() -> ModFile:
    records = [
        # campo conhecido do toolkit + campos extras
        rec(1, TypeCode.WEAPON, "Iron Sword", [
            ("description", "A heavy sword for hard people."),
            ("tooltip", "Hit them with the sharp end."),       # campo novo, texto de verdade
            ("bone name", "Right Hand"),                       # lista do original
            ("anim name", "sword_swing_01"),                   # lista do original
            ("mesh path", "data/models/sword.mesh"),           # nome do campo e valor técnicos
            ("weird code", "sword_swing_02"),                  # valor técnico, campo fora das listas
            ("_hidden", "Do not touch"),                       # começa com _
        ]),
        # registro de tipo sem texto conhecido: só frases com espaço
        rec(2, TypeCode.ANIMAL_ANIMATION, "AnimRec", [
            ("remark", "A note for the player."),
            ("mesh2", "Head"),
        ]),
        # só referência a outro arquivo: não entra
        rec(3, TypeCode.WEAPON, "Ref", [("tooltip", "Reference only text.")], flags=0b1),
    ]
    return ModFile(
        file_type=FileType.SIMPLE_HEADER, version=1, author="", description="",
        dependencies="", references="", unknown_a=0, records=records,
    )


class TechnicalReason(unittest.TestCase):
    def test_codigo(self):
        for v in ("sword.mesh", "data/models/x", "bone_left_arm", "leftArm", "Arm2", "head", "a=b",
                  "one.mesh two.mesh"):
            self.assertIsNotNone(technical_reason(v), v)

    def test_texto(self):
        for v in ("Iron Sword", "A heavy sword.", "Hello, friend!", "Swords", "1234", "Mr. Smith is here"):
            self.assertIsNone(technical_reason(v), v)


class Regras(unittest.TestCase):
    def test_cria_arquivos_padrao(self):
        with tempfile.TemporaryDirectory() as d:
            r = FieldRules.load(d)
            self.assertEqual(r.blacklist, frozenset(DEFAULT_BLACKLIST))
            self.assertEqual(len(DEFAULT_BLACKLIST), 11)
            self.assertTrue((Path(d) / BLACKLIST_FILE).exists())
            self.assertTrue((Path(d) / "translator_liberados.txt").exists())

    def test_usuario_edita(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / BLACKLIST_FILE).write_text("# x\nTooltip\n", encoding="utf-8")
            (Path(d) / "translator_liberados.txt").write_text("weird code\n", encoding="utf-8")
            r = FieldRules.load(d)
            self.assertEqual(r.blacklist, frozenset({"tooltip"}))
            self.assertEqual(r.allowlist, frozenset({"weird code"}))


class Coleta(unittest.TestCase):
    def keys(self, units):
        return {(u.string_id.split("-")[0], u.field) for u in units}

    def test_traduz_campo_novo_e_pula_lista_e_codigo(self):
        units, rep = collect_units(make_mod(), rules=FieldRules())
        k = self.keys(units)
        self.assertIn(("1", "description"), k)       # o toolkit já achava
        self.assertIn(("1", "tooltip"), k)           # novo
        self.assertNotIn(("1", "bone name"), k)      # lista
        self.assertNotIn(("1", "anim name"), k)      # lista
        self.assertNotIn(("1", "mesh path"), k)      # nome técnico
        self.assertNotIn(("1", "weird code"), k)     # valor técnico
        self.assertNotIn(("1", "_hidden"), k)
        self.assertNotIn(("3", "tooltip"), k)        # só referência
        self.assertEqual(rep.extra_units, len(units) - len(collect_units(make_mod(), extra=False)[0]))
        self.assertIn("mesh path", rep.skipped)
        self.assertIn("weird code", rep.skipped)
        self.assertNotIn("bone name", rep.skipped)   # a lista é silenciosa

    def test_tipo_sem_texto_conhecido_so_frases(self):
        units, rep = collect_units(make_mod(), rules=FieldRules())
        k = self.keys(units)
        self.assertIn(("2", "remark"), k)
        self.assertNotIn(("2", "mesh2"), k)

    def test_liberados(self):
        rules = FieldRules(allowlist=frozenset({"weird code", "mesh path"}))
        units, rep = collect_units(make_mod(), rules=rules)
        k = self.keys(units)
        self.assertIn(("1", "weird code"), k)
        self.assertIn(("1", "mesh path"), k)

    def test_blacklist_do_usuario_vence_liberados(self):
        rules = FieldRules(blacklist=frozenset({"tooltip"}), allowlist=frozenset({"tooltip"}))
        units, _ = collect_units(make_mod(), rules=rules)
        self.assertNotIn(("1", "tooltip"), self.keys(units))

    def test_sem_extras_igual_ao_toolkit(self):
        base, rep = collect_units(make_mod(), extra=False)
        self.assertEqual(rep.skipped, {})
        self.assertNotIn(("1", "tooltip"), self.keys(base))


class PontaAPonta(unittest.TestCase):
    def test_traduz_gera_e_confere(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            mod_path = tmp / "Test.mod"
            mod_path.write_bytes(dump(make_mod()))
            proj = Project.from_mod_file(mod_path, tmp / "projetos", target_lang="pt-BR")
            fields = {(u.string_id.split("-")[0], u.field) for u in proj.units}
            self.assertIn(("1", "tooltip"), fields)
            self.assertNotIn(("1", "bone name"), fields)
            self.assertTrue((tmp / BLACKLIST_FILE).exists())  # criada na pasta de dados
            self.assertIsNotNone(proj.field_report)

            report = translate_project(proj, Simulated())
            self.assertTrue(any("mesh path" in n for n in report.field_notes))
            self.assertGreater(report.translated, 0)

            built = build_translation(proj, mod_path, tmp / "out")
            self.assertEqual(built.problems, [])
            out = load(built.path.read_bytes())
            by = {(r.string_id.split("-")[0], k): v for r in out.records for k, v in r.strings}
            self.assertNotEqual(by[("1", "tooltip")], "Hit them with the sharp end.")
            # o mod traduzido é cópia completa: campos técnicos continuam, IGUAIS ao original (nunca traduzidos)
            orig = load(mod_path.read_bytes())
            orig_by = {(r.string_id.split("-")[0], k): v for r in orig.records for k, v in r.strings}
            self.assertEqual(by[("1", "bone name")], orig_by[("1", "bone name")])
            self.assertEqual(by[("1", "mesh path")], orig_by[("1", "mesh path")])
            self.assertEqual(verify_output(built.path, proj), [])

    def test_projeto_antigo_ganha_campos_novos_sem_perder_traducao(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            mod_path = tmp / "Test.mod"
            mod_path.write_bytes(dump(make_mod()))
            rules = FieldRules()
            p1 = Project.from_mod_file(mod_path, tmp / "projetos", rules=rules)
            for u in p1.units:
                if u.field == "description":
                    u.translation, u.status = "Uma espada pesada.", "revisada"
            p1.save()
            p2 = Project.from_mod_file(mod_path, tmp / "projetos", rules=rules)
            desc = [u for u in p2.units if u.field == "description"][0]
            self.assertEqual(desc.translation, "Uma espada pesada.")


if __name__ == "__main__":
    unittest.main()
