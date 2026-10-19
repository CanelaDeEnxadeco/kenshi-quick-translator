"""
Testes do núcleo. Rodam sem internet e sem o Kenshi instalado:

    python -m unittest discover -s tests -v

Para testar também com um mod de verdade, aponte KENSHI_SAMPLE_MOD para um .mod.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path

from kenshi_translator_toolkit import FileType, ModFile, RawRecord, TypeCode, dump, load

import kenshi_quick_translator.core as core_module
from kenshi_quick_translator.core import (
    Options,
    ProviderBroken,
    add_to_mods_cfg,
    build_translation,
    install_translation,
    translate_project,
    translation_filename,
    verify_output,
)
from kenshi_quick_translator.glossary import Glossary
from kenshi_quick_translator.langdetect import detect_language
from kenshi_quick_translator.markers import mask, markers_match
from kenshi_quick_translator.memory import TranslationMemory
from kenshi_quick_translator.project import ATTENTION, AUTO, IGNORED, PENDING, REVIEWED, Project
from kenshi_quick_translator.providers import Provider, ProviderError, Simulated

core_module.BACKOFF_BASE = 0.0  # nos testes não se espera entre tentativas

LINE = "Why would you /TEAMUP/ with bug people? /GETLOST/ /TRASH/!"


def make_mod(lines: list[str], name: str = "Test.mod") -> bytes:
    """Monta um .mod mínimo em memória, só com linhas de diálogo."""
    records = [
        RawRecord(
            instance_count=0, typecode=TypeCode.DIALOGUE_LINE, record_id=0,
            name="DIALOGUE_LINE", string_id=f"{i + 1}-{name}", flags=0,
            strings=[("text0", text)],
        )
        for i, text in enumerate(lines)
    ]
    mod = ModFile(
        file_type=FileType.SIMPLE_HEADER, version=1, author="", description="",
        dependencies="Dialogue.mod", references="", unknown_a=0, records=records,
    )
    return dump(mod)


def make_project(tmp: Path, lines: list[str], name: str = "Test.mod") -> tuple[Project, Path]:
    mod_path = tmp / name
    mod_path.write_bytes(make_mod(lines, name))
    proj = Project.from_mod_file(mod_path, tmp / "proj", target_lang="pt-BR")
    return proj, mod_path


class Mangling(Provider):
    """Simula um serviço que destrói as fichas de marcador (o problema real)."""

    name = "mangle"
    label = "Mangle"

    def __init__(self, ruin_tags: bool = False) -> None:
        self.ruin_tags = ruin_tags

    def translate_batch(self, texts, source, target):
        out = []
        for t in texts:
            if "ZQ" in t:
                t = t.replace("ZQ0ZQ", "").replace("ZQ", "")  # sumiu a ficha
            elif self.ruin_tags and "<x" in t:
                t = t.replace("<x0/>", "")
            out.append(f"[PT] {t}")
        return out


class Failing(Provider):
    name = "falha"
    label = "Falha"

    def translate_batch(self, texts, source, target):
        raise ProviderError("sem conexão", retryable=True)


class MarkerTests(unittest.TestCase):
    def test_roundtrip(self):
        m = mask(LINE)
        sent = m.text_for("alnum")
        self.assertNotIn("/TEAMUP/", sent)
        restored, problems = m.restore(sent)
        self.assertEqual(restored, LINE)
        self.assertEqual(problems, [])

    def test_suffix_glued_to_marker(self):
        text = "You are a /BASTARD/s."
        m = mask(text)
        restored, problems = m.restore(m.text_for())
        self.assertEqual(restored, text)
        self.assertEqual(problems, [])

    def test_service_adds_spaces_and_changes_case(self):
        m = mask("Hi /BROTHER/!")
        restored, problems = m.restore("Oi zq 0 zq!")
        self.assertEqual(restored, "Oi /BROTHER/!")
        self.assertEqual(problems, [])

    def test_lost_marker_is_reported(self):
        m = mask("Hi /BROTHER/!")
        _, problems = m.restore("Oi!")
        self.assertTrue(problems)

    def test_duplicated_marker_is_reported(self):
        m = mask("Hi /BROTHER/!")
        _, problems = m.restore("Oi ZQ0ZQ ZQ0ZQ!")
        self.assertTrue(problems)

    def test_markers_match(self):
        self.assertTrue(markers_match("a /X1/ b", "c /X1/ d"))
        self.assertFalse(markers_match("a /X1/ b", "c d"))
        self.assertFalse(markers_match("a /X1/ b", "c /X1/ /X1/"))


class GlossaryTests(unittest.TestCase):
    def test_translates_and_keeps(self):
        g = Glossary({"Holy Nation": "Nação Sagrada", "Hub": None})
        m = mask("The Holy Nation hates the Hub.", g)
        restored, problems = m.restore(m.text_for())
        self.assertEqual(restored, "The Nação Sagrada hates the Hub.")
        self.assertEqual(problems, [])

    def test_whole_words_only(self):
        g = Glossary({"Hub": "Centro"})
        self.assertEqual(g.find("Hubert went to Hubs"), [])

    def test_default_glossary_loads(self):
        self.assertIn("Holy Nation", Glossary.default().terms)


class LangTests(unittest.TestCase):
    def test_languages(self):
        self.assertEqual(detect_language(["I don't owe you answers.", "You talk too much and I am not your friend."])[0], "en")
        self.assertEqual(detect_language(["Eu não devo respostas a você.", "Você fala demais e não é meu amigo."])[0], "pt")
        self.assertEqual(detect_language(["No te debo respuestas.", "Hablas demasiado y no eres mi amigo."])[0], "es")
        self.assertEqual(detect_language(["Я не должен тебе ответов."])[0], "ru")
        self.assertEqual(detect_language(["..."])[0], "und")


class MemoryTests(unittest.TestCase):
    def test_put_get_overwrite(self):
        tm = TranslationMemory()
        self.assertIsNone(tm.get("a", "pt-BR"))
        tm.put("a", "pt-BR", "b")
        tm.put("a", "pt-BR", "c", origin="revisao")
        self.assertEqual(tm.get("a", "pt-BR"), "c")
        self.assertEqual(tm.count(), 1)


class TranslateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_markers_survive_and_duplicates_sent_once(self):
        proj, _ = make_project(self.tmp, [LINE, "Maybe.", "Maybe.", "..."])
        prov = Simulated()
        rep = translate_project(proj, prov, memory=TranslationMemory())
        sent = [t for call in prov.calls for t in call]
        self.assertEqual(len([t for t in sent if t == "Maybe."]), 1)  # texto repetido vai uma vez só
        self.assertEqual(rep.translated, 3)
        self.assertEqual(rep.ignored, 1)  # "..." não tem letras
        for u in proj.units:
            if u.status == AUTO:
                self.assertTrue(markers_match(u.source, u.translation))
        line = next(u for u in proj.units if u.source == LINE)
        self.assertIn("/TEAMUP/", line.translation)

    def test_memory_is_used_on_second_run(self):
        mem = TranslationMemory()
        p1, _ = make_project(self.tmp, ["Hello there."], "A.mod")
        translate_project(p1, Simulated(), memory=mem)
        p2, _ = make_project(self.tmp, ["Hello there."], "B.mod")
        prov = Simulated()
        rep = translate_project(p2, prov, memory=mem)
        self.assertEqual(rep.from_memory, 1)
        self.assertEqual(prov.calls, [])

    def test_service_destroying_markers_is_recovered_by_parts(self):
        proj, _ = make_project(self.tmp, [LINE])
        rep = translate_project(proj, Mangling(ruin_tags=True))
        u = proj.units[0]
        self.assertEqual(u.status, ATTENTION)  # pede conferência, mas está salvo
        self.assertTrue(markers_match(u.source, u.translation))
        self.assertEqual(rep.attention, 1)

    def test_tag_style_recovers_when_alnum_fails(self):
        proj, _ = make_project(self.tmp, [LINE])
        translate_project(proj, Mangling(ruin_tags=False))
        u = proj.units[0]
        self.assertEqual(u.status, AUTO)
        self.assertTrue(markers_match(u.source, u.translation))

    def test_glossary_applied_in_translation(self):
        proj, _ = make_project(self.tmp, ["The Holy Nation is coming."])
        translate_project(proj, Simulated(), glossary=Glossary({"Holy Nation": "Nação Sagrada"}))
        self.assertIn("Nação Sagrada", proj.units[0].translation)

    def test_character_names_kept_by_default(self):
        mod_path = self.tmp / "C.mod"
        rec = RawRecord(instance_count=0, typecode=TypeCode.CHARACTER, record_id=0, name="Saelith",
                        string_id="1-C.mod", flags=0, strings=[])
        mod_path.write_bytes(dump(ModFile(file_type=FileType.SIMPLE_HEADER, version=1, author="", description="",
                                          dependencies="", references="", unknown_a=0, records=[rec])))
        proj = Project.from_mod_file(mod_path, self.tmp / "proj")
        translate_project(proj, Simulated())
        self.assertEqual(proj.units[0].status, IGNORED)

    def test_reviewed_is_never_overwritten(self):
        proj, _ = make_project(self.tmp, ["Hello."])
        proj.set_translation(proj.units[0].key, "Olá, viajante.")
        translate_project(proj, Simulated(), options=Options(retranslate=True))
        self.assertEqual(proj.units[0].translation, "Olá, viajante.")
        self.assertEqual(proj.units[0].status, REVIEWED)

    def test_provider_down_stops_and_keeps_progress(self):
        proj, _ = make_project(self.tmp, [f"Line number {i}." for i in range(6)])
        with self.assertRaises(ProviderBroken):
            translate_project(proj, Failing(), options=Options(chunk_size=1, workers=1))
        self.assertTrue(all(u.status == PENDING for u in proj.units))  # nada perdido nem estragado
        self.assertTrue(proj.path.exists())

    def test_cancel(self):
        proj, _ = make_project(self.tmp, [f"Line number {i}." for i in range(5)])
        ev = threading.Event()
        ev.set()
        rep = translate_project(proj, Simulated(), cancel=ev, options=Options(chunk_size=1, workers=1))
        self.assertTrue(rep.cancelled)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_load_and_rescan_keeps_work(self):
        proj, mod_path = make_project(self.tmp, ["One line.", "Two lines."])
        translate_project(proj, Simulated())
        proj.set_translation(proj.units[0].key, "Uma linha.")
        proj.save()
        again = Project.from_mod_file(mod_path, self.tmp / "proj")  # "procurar mods de novo"
        self.assertEqual(again.units[0].translation, "Uma linha.")
        self.assertEqual(again.units[0].status, REVIEWED)
        self.assertEqual(again.units[1].status, AUTO)

    def test_changed_source_needs_attention(self):
        proj, mod_path = make_project(self.tmp, ["One line."])
        translate_project(proj, Simulated())
        proj.save()
        mod_path.write_bytes(make_mod(["One line, updated."]))  # o autor atualizou o mod
        again = Project.from_mod_file(mod_path, self.tmp / "proj")
        self.assertEqual(again.units[0].status, ATTENTION)
        self.assertEqual(again.units[0].translation, "")

    def test_po_roundtrip(self):
        proj, _ = make_project(self.tmp, ["Hello there."])
        # O primeiro msgstr "" do PO é o cabeçalho; a tradução é o último.
        head, _, tail = proj.export_po().rpartition('msgstr ""')
        po = head + 'msgstr "Olá."' + tail
        self.assertEqual(proj.import_po(po), 1)
        self.assertEqual(proj.units[0].translation, "Olá.")
        self.assertEqual(proj.units[0].status, REVIEWED)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_build_and_verify(self):
        proj, mod_path = make_project(self.tmp, [LINE, "Maybe."])
        before = mod_path.read_bytes()
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        self.assertEqual(res.problems, [])
        self.assertEqual(res.path.name, "Test.mod")  # mesmo nome do original
        self.assertEqual(mod_path.read_bytes(), before)  # original intacto
        mod = load(res.path.read_bytes())
        self.assertNotIn("Test.mod", mod.dependencies)  # não depende de si mesmo

    def test_verify_catches_tampering(self):
        proj, mod_path = make_project(self.tmp, [LINE])
        translate_project(proj, Simulated())
        res = build_translation(proj, mod_path, self.tmp / "out")
        proj.units[0].translation = "mudou depois"
        self.assertTrue(verify_output(res.path, proj))

    def test_filename(self):
        self.assertEqual(translation_filename("Kaizo.mod", "pt-BR"), "Kaizo.mod")
        self.assertEqual(translation_filename("Kaizo.mod", "ru"), "Kaizo.mod")  # o idioma não entra no nome
        self.assertEqual(translation_filename("Kaizo.mod.original", "ru"), "Kaizo.mod")


class ModsCfgTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_inserted_after_original_with_backup_and_crlf(self):
        cfg = self.tmp / "mods.cfg"
        cfg.write_bytes(b"A.mod\r\nTest.mod\r\nZ.mod\r\n")
        self.assertTrue(add_to_mods_cfg(cfg, "Test PT-BR.mod", after="Test.mod"))
        self.assertEqual(cfg.read_bytes(), b"A.mod\r\nTest.mod\r\nTest PT-BR.mod\r\nZ.mod\r\n")
        self.assertEqual(len(list(self.tmp.glob("mods.cfg.bak-*"))), 1)

    def test_idempotent(self):
        cfg = self.tmp / "mods.cfg"
        cfg.write_text("Test.mod\nTest PT-BR.mod\n")
        self.assertFalse(add_to_mods_cfg(cfg, "Test PT-BR.mod", after="Test.mod"))

    def test_original_missing_appends(self):
        cfg = self.tmp / "mods.cfg"
        cfg.write_text("A.mod\n")
        add_to_mods_cfg(cfg, "X PT-BR.mod", after="X.mod")
        self.assertEqual(cfg.read_text(), "A.mod\nX PT-BR.mod\n")

    def test_install(self):
        kenshi = self.tmp / "Kenshi"
        (kenshi / "data").mkdir(parents=True)
        (kenshi / "data" / "mods.cfg").write_text("Test.mod\n")
        built = self.tmp / "out" / "Test.mod"
        built.parent.mkdir()
        built.write_bytes(b"x")
        dest, changed = install_translation(kenshi, built, "Test.mod")
        self.assertEqual(dest, kenshi / "mods" / "Test" / "Test.mod")
        self.assertTrue(dest.exists())
        self.assertFalse(changed)  # já estava no mods.cfg: nada a acrescentar
        self.assertEqual((kenshi / "data" / "mods.cfg").read_text(), "Test.mod\n")


@unittest.skipUnless(os.environ.get("KENSHI_SAMPLE_MOD"), "defina KENSHI_SAMPLE_MOD para testar com um mod real")
class RealModTests(unittest.TestCase):
    def test_real_mod_end_to_end(self):
        path = Path(os.environ["KENSHI_SAMPLE_MOD"])
        raw = path.read_bytes()
        self.assertEqual(dump(load(raw)), raw)  # leitura fiel, byte a byte
        with tempfile.TemporaryDirectory() as d:
            proj = Project.from_mod_file(path, Path(d) / "proj")
            translate_project(proj, Simulated())
            res = build_translation(proj, path, Path(d) / "out")
            self.assertEqual(res.problems, [])
            self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
