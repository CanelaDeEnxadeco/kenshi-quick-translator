"""0.6.4: textos que o mod altera em registros do jogo base (flag 1) passam a ser traduzidos."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_translator_toolkit import dump, load  # noqa: E402
from kenshi_translator_toolkit.domain.entities.typecode import FileType, TypeCode  # noqa: E402
from kenshi_translator_toolkit.format.mod_file import ModFile, RawRecord  # noqa: E402

from kenshi_quick_translator.core import MODE_DEPENDENT, build_translation  # noqa: E402
from kenshi_quick_translator.fields import collect_units  # noqa: E402
from kenshi_quick_translator.project import Project  # noqa: E402


def rec(sid, typecode, name, flags, strings=(), refs=()):
    return RawRecord(instance_count=0, typecode=typecode, record_id=0, name=name, string_id=sid,
                     flags=flags, strings=list(strings), references=list(refs))


def make():
    recs = [
        rec("1-X.mod", TypeCode.DIALOGUE_LINE, "DIALOGUE_LINE1", 0, [("text0", "Own line, hello there.")]),
        rec("2-Dialogue.mod", TypeCode.DIALOGUE_LINE, "DIALOGUE_LINE2", 0x2A5F31, [("text0", "Pay us 2,000 of your creds.")]),
        rec("3-gamedata.base", TypeCode.ITEM, "Vanilla Sword Name", 0x2A5F31, [("description", "A sword from the Empire.")]),
        rec("4-gamedata.base", TypeCode.DIALOGUE_LINE, "DIALOGUE_LINE4", 0x2A5F31, [], [("x", [("5-gamedata.base", 0, 0, 0)])]),
        rec("6-X.mod", TypeCode.ITEM, "New Item Name", 0x2A5F33, [("description", "A brand new thing.")]),
    ]
    mod = ModFile(file_type=FileType.SIMPLE_HEADER, version=1, author="", description="d",
                  dependencies="gamedata.base", references="", unknown_a=7, records=recs)
    return dump(mod)


class TextoAlteradoDoJogoBase(unittest.TestCase):
    def test_coleta(self):
        mod = load(make())
        antes, _ = collect_units(mod, changed_base=False)
        depois, rep = collect_units(mod)
        self.assertEqual(len(depois) - len(antes), 2)
        self.assertEqual(rep.changed_base_units, 2)
        keys = {(u.string_id, u.field) for u in depois}
        self.assertIn(("2-Dialogue.mod", "text0"), keys)
        self.assertIn(("3-gamedata.base", "description"), keys)
        self.assertNotIn(("3-gamedata.base", ""), keys)  # nunca o nome do registro do jogo base

    def test_build_nos_dois_modos(self):
        for mode in ("completo", MODE_DEPENDENT):
            with tempfile.TemporaryDirectory() as t:
                tmp = Path(t)
                mp = tmp / "X.mod"
                mp.write_bytes(make())
                proj = Project.from_mod_file(mp, tmp / "proj", target_lang="pt-BR")
                self.assertEqual(len(proj.units), 5)  # própria + 2 do jogo base + nome e texto do registro novo
                for u in proj.units:
                    u.translation = "PT| " + u.source
                res = build_translation(proj, mp, tmp / "out", mode=mode)
                self.assertEqual(res.problems, [])
                out = load(res.path.read_bytes())
                texts = [v for r in out.records for _, v in r.strings]
                self.assertIn("PT| Pay us 2,000 of your creds.", texts)
                self.assertIn("PT| A sword from the Empire.", texts)
                names = [r.name for r in out.records]
                self.assertNotIn("PT| Vanilla Sword Name", names)


if __name__ == "__main__":
    unittest.main()
