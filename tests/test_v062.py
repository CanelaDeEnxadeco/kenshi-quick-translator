"""Cabeçalho estendido (tipo 17): o tamanho do cabeçalho tem que acompanhar a descrição."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kenshi_translator_toolkit import dump, load  # noqa: E402
from kenshi_translator_toolkit.domain.entities.typecode import FileType, TypeCode  # noqa: E402
from kenshi_translator_toolkit.format.mod_file import ModFile, RawRecord  # noqa: E402

from kenshi_quick_translator.core import build_translation, set_description  # noqa: E402
from kenshi_quick_translator.project import Project  # noqa: E402


def extended_mod(lines, description="Descrição 募 do mod", gap=b"\x01"):
    """Mod de cabeçalho estendido como o do Another World of RO (header_length conta a descrição)."""
    recs = [RawRecord(instance_count=0, typecode=TypeCode.DIALOGUE_LINE, record_id=0, name="DIALOGUE_LINE",
                      string_id=f"{i + 1}-X.mod", flags=0, strings=[("text0", t)]) for i, t in enumerate(lines)]
    mod = ModFile(file_type=FileType.EXTENDED_HEADER, version=1, author="", description=description,
                  dependencies="gamedata.base", references="", unknown_a=7, records=recs,
                  header_length=0, unknown_b=0, unknown_c=0, header_gap=gap, unknown_d=1)
    tell = 4 + 4 + 4 + 4 + 4 + len(description.encode()) + 4 + len(mod.dependencies) + 4 + 4 + 4 + 1  # até unknown_c
    mod.header_length = tell + len(gap) - 8
    out = dump(mod)
    assert load(out).header_length == mod.header_length
    return out


class CabecalhoEstendido(unittest.TestCase):
    def test_build_completo_le_de_volta_e_confere(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            mp = tmp / "X.mod"
            mp.write_bytes(extended_mod(["Hello there.", "Good day, traveler."]))
            proj = Project.from_mod_file(mp, tmp / "proj", target_lang="pt-BR")
            for u in proj.units:
                u.translation = "Olá."
            res = build_translation(proj, mp, tmp / "out")
            self.assertEqual(res.problems, [])
            raw = res.path.read_bytes()
            m = load(raw)  # antes da correção: ValueError (arquivo "corrompido")
            self.assertEqual(len(m.records), 2)
            self.assertEqual(dump(m), raw)
            self.assertIn("[Kenshi Quick Translator: pt-BR]", m.description)
            self.assertEqual(m.header_gap, b"\x01")

    def test_set_description_acompanha_o_tamanho(self):
        m = load(extended_mod(["a b c"]))
        before = m.header_length
        set_description(m, m.description + "\n[Kenshi Quick Translator: pt-BR] é só um teste")
        grown = len(m.description.encode()) - len("Descrição 募 do mod".encode())
        self.assertEqual(m.header_length, before + grown)
        out = dump(m)
        self.assertEqual(dump(load(out)), out)

    def test_cabecalho_simples_nao_muda(self):
        from test_core import make_mod
        m = load(make_mod(["x y z"]))
        set_description(m, "nova")
        self.assertIsNone(m.header_length)


if __name__ == "__main__":
    unittest.main()
