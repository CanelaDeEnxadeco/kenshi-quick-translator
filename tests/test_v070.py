"""0.7.0: modo seguro, campos extras só de tipos de registro que o jogador vê (dica do Kakrain)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_translator_toolkit import FileType, ModFile, RawRecord, TypeCode

from kenshi_quick_translator.config import Config
from kenshi_quick_translator.fields import FieldRules, collect_units, is_visible_type


def rec(i, typecode, name, strings, flags=0):
    return RawRecord(instance_count=0, typecode=typecode, record_id=0, name=name,
                     string_id=f"{i}-Test.mod", flags=flags, strings=strings)


def make_mod() -> ModFile:
    records = [
        rec(1, TypeCode.WEAPON, "Sword", [("tooltip", "Hit them with the sharp end.")]),
        rec(2, TypeCode.DIALOGUE, "Talk", [("extra note", "Say hello to the stranger.")]),
        rec(3, TypeCode.DIALOGUE_LINE, "Line", [("text", "Welcome to my shop, friend.")]),
        rec(4, TypeCode.ANIMATION_FILE, "Anim", [("remark", "Some long animation remark here.")]),
        rec(5, TypeCode.EFFECT, "Fx", [("remark", "Sparks fly from the blade.")]),
        rec(6, TypeCode.TUTORIAL, "Tut", [("remark", "Press the button to continue.")]),
    ]
    return ModFile(file_type=FileType.SIMPLE_HEADER, version=1, author="", description="",
                   dependencies="", references="", unknown_a=0, records=records)


class ModoSeguro(unittest.TestCase):
    def keys(self, units):
        return {(u.string_id.split("-")[0], u.field) for u in units}

    def test_padrao_ignora_tipos_tecnicos(self):
        units, rep = collect_units(make_mod(), rules=FieldRules())
        k = self.keys(units)
        self.assertIn(("1", "tooltip"), k)
        self.assertIn(("2", "extra note"), k)   # DIALOGUE
        self.assertIn(("3", "text"), k)         # DIALOGUE_LINE
        self.assertIn(("6", "remark"), k)       # TUTORIAL
        self.assertNotIn(("4", "remark"), k)    # ANIMATION_FILE
        self.assertNotIn(("5", "remark"), k)    # EFFECT
        self.assertEqual(rep.technical_types, {"ANIMATION_FILE": 1, "EFFECT": 1})
        self.assertTrue(any("ANIMATION_FILE" in ln for ln in rep.lines()))

    def test_desligado_volta_ao_comportamento_antigo(self):
        units, rep = collect_units(make_mod(), rules=FieldRules(), safe_types=False)
        k = self.keys(units)
        self.assertIn(("4", "remark"), k)
        self.assertIn(("5", "remark"), k)
        self.assertEqual(rep.technical_types, {})

    def test_is_visible_type(self):
        for t in (TypeCode.WEAPON, TypeCode.DIALOGUE, TypeCode.DIALOGUE_LINE, TypeCode.DIALOGUE_PACKAGE, TypeCode.TUTORIAL):
            self.assertTrue(is_visible_type(t), t)
        for t in (TypeCode.ANIMATION_FILE, TypeCode.EFFECT, TypeCode.ANIMATION, TypeCode.AI_PACKAGE):
            self.assertFalse(is_visible_type(t), t)

    def test_config_padrao_ligado(self):
        self.assertTrue(Config().safe_record_types)


if __name__ == "__main__":
    unittest.main()
