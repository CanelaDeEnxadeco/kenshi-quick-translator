"""Testes de várias chaves do mesmo serviço (KeyPool)."""

import tempfile
import time
import unittest
from pathlib import Path

import kenshi_quick_translator.core as core_module
from kenshi_quick_translator.core import Options, translate_project
from kenshi_quick_translator.project import AUTO
from kenshi_quick_translator.providers import DeepL, KeyPool, Provider, ProviderError, Simulated, make_provider, split_keys

from test_core import make_project

core_module.BACKOFF_BASE = 0.0


class Dead(Provider):
    """Chave sem cota: toda chamada falha."""

    name, label = "deepl", "DeepL (morta)"

    def __init__(self):
        self.calls = 0

    def translate_batch(self, texts, source, target):
        self.calls += 1
        raise ProviderError("Cota do serviço esgotada (456).")


class KeyPoolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_split_keys(self):
        self.assertEqual(split_keys("a:fx; b:fx\nc:fx;;a:fx"), ["a:fx", "b:fx", "c:fx"])
        self.assertEqual(split_keys("  "), [])

    def test_make_provider_builds_pool_only_for_several_keys(self):
        self.assertIsInstance(make_provider("deepl", "k1:fx"), DeepL)
        pool = make_provider("deepl", "k1:fx;k2:fx;k3:fx")
        self.assertIsInstance(pool, KeyPool)
        self.assertEqual(len(pool.members), 3)
        self.assertIn("3 chaves", pool.label)

    def test_batches_are_shared_between_keys(self):
        a, b, c = Simulated(), Simulated(), Simulated()
        pool = KeyPool([a, b, c])
        proj, _ = make_project(self.tmp, [f"Unique line number {i} here." for i in range(60)])
        translate_project(proj, pool, options=Options(chunk_size=2, workers=3))
        counts = [len(p.calls) for p in (a, b, c)]
        self.assertEqual(sum(counts), 30)
        self.assertTrue(all(8 <= n <= 12 for n in counts), counts)  # repartido de forma parecida
        self.assertTrue(all(u.status == AUTO for u in proj.units))

    def test_dead_key_does_not_stop_the_translation(self):
        dead, good = Dead(), Simulated()
        pool = KeyPool([dead, good])
        proj, _ = make_project(self.tmp, [f"Unique line number {i} here." for i in range(40)])
        rep = translate_project(proj, pool, options=Options(chunk_size=2, workers=2))
        self.assertTrue(all(u.status == AUTO for u in proj.units))
        self.assertEqual(rep.failed, 0)
        self.assertLessEqual(dead.calls, KeyPool.SKIP_AFTER + 2)  # deixada de lado depois de falhar

    def test_all_keys_dead_reports_the_error(self):
        pool = KeyPool([Dead(), Dead()])
        with self.assertRaises(ProviderError):
            pool.translate_batch(["x"], "en", "pt-BR")

    def test_test_names_the_failing_key(self):
        pool = KeyPool([Simulated(), Dead()])
        with self.assertRaisesRegex(ProviderError, "chave 2"):
            pool.test()

    def test_two_keys_double_the_throughput_when_each_has_its_own_limit(self):
        """Cada chave aceita 1 pedido por vez (serviço 'educado'): com 2 chaves, 2 pedidos ao mesmo tempo."""
        import threading

        class OneAtATime(Provider):
            name, label = "deepl", "Uma por vez"

            def __init__(self):
                self.lock = threading.Lock()

            def translate_batch(self, texts, source, target):
                with self.lock:  # uma chave só atende um pedido de cada vez
                    time.sleep(0.04)
                return [f"[PT] {t}" for t in texts]

        def run(provider):
            proj, _ = make_project(self.tmp / f"r{id(provider)}", [f"Unique line number {i} here." for i in range(32)]) \
                if (self.tmp / f"r{id(provider)}").mkdir() is None else (None, None)
            t0 = time.monotonic()
            translate_project(proj, provider, options=Options(chunk_size=1, workers=8))
            return time.monotonic() - t0

        one = run(OneAtATime())
        two = run(KeyPool([OneAtATime(), OneAtATime()]))
        self.assertLess(two, one * 0.7, f"1 chave={one:.2f}s 2 chaves={two:.2f}s")


if __name__ == "__main__":
    unittest.main()
