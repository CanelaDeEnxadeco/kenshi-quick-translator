"""Testes de velocidade (paralelismo, limite automático, gravação) e de vários idiomas de origem."""

import tempfile
import threading
import time
import unittest
from pathlib import Path

import kenshi_quick_translator.core as core_module
from kenshi_quick_translator.core import Options, Throttle, analyze_languages, translate_project
from kenshi_quick_translator.langdetect import detect_text, same_language
from kenshi_quick_translator.memory import TranslationMemory
from kenshi_quick_translator.project import AUTO, IGNORED, Project
from kenshi_quick_translator.providers import Provider, ProviderError, Simulated

from test_core import make_mod, make_project

core_module.BACKOFF_BASE = 0.0


def lines(n: int) -> list[str]:
    return [f"Unique dialogue line number {i} for testing speed." for i in range(n)]


class SpeedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_with(self, workers: int) -> float:
        proj, _ = make_project(self.tmp / f"w{workers}", lines(24)) if (self.tmp / f"w{workers}").mkdir() is None else (None, None)
        prov = Simulated(delay=0.05)
        t0 = time.monotonic()
        translate_project(proj, prov, options=Options(chunk_size=1, workers=workers))
        elapsed = time.monotonic() - t0
        self.assertTrue(all(u.status == AUTO for u in proj.units))
        return elapsed

    def test_parallel_is_much_faster_than_serial(self):
        serial = self.run_with(1)
        parallel = self.run_with(6)
        self.assertLess(parallel, serial * 0.5, f"serial={serial:.2f}s paralelo={parallel:.2f}s")

    def test_result_is_identical_regardless_of_workers(self):
        a, _ = make_project(self.tmp / "a", lines(30)) if (self.tmp / "a").mkdir() is None else (None, None)
        b, _ = make_project(self.tmp / "b", lines(30)) if (self.tmp / "b").mkdir() is None else (None, None)
        translate_project(a, Simulated(), options=Options(chunk_size=3, workers=1))
        translate_project(b, Simulated(), options=Options(chunk_size=3, workers=8))
        self.assertEqual([u.translation for u in a.units], [u.translation for u in b.units])  # ordem preservada

    def test_throttle_adapts_when_service_complains(self):
        """Serviço que só aceita 2 pedidos ao mesmo tempo: o programa baixa sozinho e termina tudo."""

        class Picky(Provider):
            name, label = "picky", "Picky"

            def __init__(self):
                self.active = 0
                self.peak = 0
                self.errors = 0
                self.lock = threading.Lock()

            def translate_batch(self, texts, source, target):
                with self.lock:
                    self.active += 1
                    self.peak = max(self.peak, self.active)
                    over = self.active > 2
                try:
                    time.sleep(0.02)
                    if over:
                        with self.lock:
                            self.errors += 1
                        raise ProviderError("429 muitos pedidos", retryable=True)
                    return [f"[PT] {t}" for t in texts]
                finally:
                    with self.lock:
                        self.active -= 1

        proj, _ = make_project(self.tmp, lines(30))
        prov = Picky()
        rep = translate_project(proj, prov, options=Options(chunk_size=1, workers=8))
        self.assertEqual(rep.failed, 0)
        self.assertTrue(all(u.status == AUTO for u in proj.units))
        self.assertGreater(prov.errors, 0)  # o serviço reclamou de verdade
        self.assertLessEqual(rep.workers_used, 8)

    def test_throttle_class(self):
        t = Throttle(8)
        t.on_throttled()
        self.assertEqual(t.limit, 4)
        t.on_throttled()
        t.on_throttled()
        t.on_throttled()
        self.assertEqual(t.limit, 1)  # nunca zera
        for _ in range(5):
            t.on_success()
        self.assertEqual(t.limit, 2)  # volta a subir aos poucos

    def test_project_is_not_saved_on_every_chunk(self):
        proj, _ = make_project(self.tmp, lines(60))
        saves = []
        real = proj.save
        proj.save = lambda *a, **k: (saves.append(1), real(*a, **k))[1]
        translate_project(proj, Simulated(), options=Options(chunk_size=1, workers=4, save_interval=60))
        self.assertLessEqual(len(saves), 3, f"gravou {len(saves)} vezes")
        self.assertEqual(Project.load(proj.path).stats()["automatica"], 60)  # e o final está completo

    def test_memory_bulk_calls(self):
        tm = TranslationMemory()
        tm.put_many([(f"s{i}", f"t{i}") for i in range(1200)], "pt-BR")
        got = tm.get_many([f"s{i}" for i in range(1500)], "pt-BR")
        self.assertEqual(len(got), 1200)  # passa dos 500 por consulta sem problema
        self.assertEqual(got["s7"], "t7")


class DetectTextTests(unittest.TestCase):
    def test_chinese_short_and_long(self):
        self.assertEqual(detect_text("你好"), "zh")
        self.assertEqual(detect_text("我不需要你的怜悯。"), "zh")

    def test_japanese_korean_russian(self):
        self.assertEqual(detect_text("ありがとう"), "ja")
        self.assertEqual(detect_text("안녕하세요"), "ko")
        self.assertEqual(detect_text("Я не должен тебе ответов."), "ru")

    def test_english_and_portuguese_sentences(self):
        self.assertEqual(detect_text("You talk too much and I am not your friend."), "en")
        self.assertEqual(detect_text("Você fala demais e não é meu amigo."), "pt")

    def test_short_latin_is_undecided(self):
        self.assertEqual(detect_text("Maybe."), "und")
        self.assertEqual(detect_text("..."), "und")

    def test_mixed_scripts_are_undecided(self):
        self.assertEqual(detect_text("Press 你好 to continue now please"), "und")

    def test_markers_do_not_count(self):
        self.assertEqual(detect_text("/BROTHER/ 你好 /TEAMUP/"), "zh")

    def test_same_language(self):
        self.assertTrue(same_language("pt", "pt-BR"))
        self.assertFalse(same_language("en", "pt-BR"))


MIXED = [
    "You talk too much and I am not your friend.",  # en
    "我不需要你的怜悯，别再烦我了。",  # zh
    "Why would you go with me? I do not trust you at all.",  # en
    "你为什么要跟我走？",  # zh
    "Você fala demais e não é meu amigo.",  # já em português
    "Maybe.",  # curto: não dá para saber
    "Come with me /TEAMUP/ now, you fool.",  # en com marcador
]


class MultiSourceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_each_text_goes_with_its_own_language(self):
        proj, _ = make_project(self.tmp, MIXED)
        prov = Simulated()
        rep = translate_project(proj, prov, options=Options(multi_source=True, source_langs=("en", "zh")))
        sent = dict()
        for texts, src in zip(prov.calls, prov.sources):
            for t in texts:
                sent[t] = src
        zh_sent = [t for t, s in sent.items() if s == "zh"]
        en_sent = [t for t, s in sent.items() if s == "en"]
        self.assertEqual(len(zh_sent), 2)
        self.assertEqual(len(en_sent), 3)  # inclui o do marcador
        self.assertEqual(sent.get("Maybe."), "auto")  # curto: o serviço decide
        self.assertTrue(rep.languages.get("zh") == 2 and rep.languages.get("en") == 3)

    def test_text_already_in_target_language_is_skipped(self):
        proj, _ = make_project(self.tmp, MIXED)
        prov = Simulated()
        translate_project(proj, prov, options=Options(multi_source=True))
        pt = next(u for u in proj.units if u.source.startswith("Você fala"))
        self.assertEqual(pt.status, IGNORED)
        self.assertEqual(pt.translation, "")
        sent = [t for texts in prov.calls for t in texts]
        self.assertNotIn(pt.source, sent)

    def test_marker_survives_in_mixed_mode(self):
        proj, _ = make_project(self.tmp, MIXED)
        translate_project(proj, Simulated(), options=Options(multi_source=True))
        u = next(u for u in proj.units if "/TEAMUP/" in u.source)
        self.assertIn("/TEAMUP/", u.translation)

    def test_unlisted_language_falls_back_to_auto(self):
        proj, _ = make_project(self.tmp, MIXED)
        prov = Simulated()
        translate_project(proj, prov, options=Options(multi_source=True, source_langs=("en",)))  # chinês não listado
        sent = {}
        for texts, src in zip(prov.calls, prov.sources):
            for t in texts:
                sent[t] = src
        self.assertEqual(sent["你为什么要跟我走？"], "auto")  # traduzido mesmo assim, com detecção do serviço
        self.assertEqual(sent["You talk too much and I am not your friend."], "en")

    def test_single_language_mode_is_unchanged(self):
        proj, _ = make_project(self.tmp, MIXED)
        proj.source_lang = "en"
        prov = Simulated()
        translate_project(proj, prov, options=Options())
        self.assertEqual(set(prov.sources), {"en"})  # tudo com o idioma escolhido, como no original

    def test_analyze_languages_without_translating(self):
        proj, _ = make_project(self.tmp, MIXED)
        counts = analyze_languages(proj)
        self.assertEqual(counts.get("zh"), 2)
        self.assertEqual(counts.get("pt"), 1)
        self.assertTrue(all(u.status == "pendente" for u in proj.units))

    def test_language_is_saved_in_project(self):
        proj, mod_path = make_project(self.tmp, MIXED)
        translate_project(proj, Simulated(), options=Options(multi_source=True))
        again = Project.from_mod_file(mod_path, self.tmp / "proj")
        self.assertEqual(sorted(u.lang for u in again.units if u.lang == "zh"), ["zh", "zh"])


if __name__ == "__main__":
    unittest.main()
