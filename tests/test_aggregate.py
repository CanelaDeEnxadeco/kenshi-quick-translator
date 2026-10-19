"""Testes do agregado e dos serviços gratuitos, sem internet (serviços falsos)."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kenshi_quick_translator.core import copy_mod_to_game
from kenshi_quick_translator.freeproviders import Aggregate, FreeService, make_free, ms_signature
from kenshi_quick_translator.providers import ProviderError


class Fake(FreeService):
    def __init__(self, name, fail_status=None, fail_after=None, max_chars=1000):
        super().__init__(rpm=100000)
        self.name = self.short = name
        self.max_chars = max_chars
        self.fail_status = fail_status
        self.fail_after = fail_after  # falha depois de N textos (falha parcial)
        self.calls = 0

    def _one(self, text, source, target):
        self.calls += 1
        if self.fail_status is not None and (self.fail_after is None or self.calls > self.fail_after):
            e = ProviderError(f"HTTP {self.fail_status}", retryable=True)
            e.status = self.fail_status
            raise e
        return f"{self.name}:{text}"


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def agg(members, clock=None, events=None):
    clock = clock or Clock()
    slept = []
    a = Aggregate(members, on_event=(events.append if events is not None else None),
                  sleep=lambda s: (slept.append(s), setattr(clock, "t", clock.t + s)), clock=clock)
    return a, clock, slept


class AggregateTests(unittest.TestCase):
    def test_429_passa_para_o_proximo_no_mesmo_lote(self):
        g, b = Fake("Google", 429), Fake("Bing")
        ev = []
        a, _, _ = agg([g, b], events=ev)
        self.assertEqual(a.translate_batch(["a", "b", "c"], "en", "pt-BR"), ["Bing:a", "Bing:b", "Bing:c"])
        self.assertTrue(any("Google bloqueou" in m and "Passei para o Bing" in m for m in ev), ev)

    def test_quarentena_e_volta_depois(self):
        g, b = Fake("Google", 429), Fake("Bing")
        a, clock, _ = agg([g, b])
        a.translate_batch(["a"], "en", "pt-BR")
        n = g.calls
        a.translate_batch(["b"], "en", "pt-BR")
        self.assertEqual(g.calls, n)  # em quarentena: nem tentou
        clock.t += 61
        g.fail_status = None
        self.assertEqual(a.translate_batch(["c"], "en", "pt-BR"), ["Google:c"])

    def test_falha_parcial_aproveita_o_que_ja_veio(self):
        g, b = Fake("Google", 429, fail_after=2), Fake("Bing")
        a, _, _ = agg([g, b])
        self.assertEqual(a.translate_batch(["a", "b", "c", "d"], "en", "pt-BR"),
                         ["Google:a", "Google:b", "Bing:c", "Bing:d"])

    def test_todos_falham_espera_e_so_entao_desiste(self):
        a, _, slept = agg([Fake("Google", 429), Fake("Bing", 503)])
        with self.assertRaises(ProviderError) as cm:
            a.translate_batch(["a"], "en", "pt-BR")
        self.assertIn("Todos os serviços falharam", str(cm.exception))
        self.assertGreaterEqual(len(slept), 3)

    def test_todos_bloqueados_mas_um_volta_durante_a_espera(self):
        g, b = Fake("Google", 429), Fake("Bing", 429)
        a, clock, _ = agg([g, b])
        orig = a._pause

        def pause(s):  # depois da primeira espera, o Bing "melhora"
            b.fail_status = None
            orig(s)

        a._pause = pause
        self.assertEqual(a.translate_batch(["a"], "en", "pt-BR"), ["Bing:a"])

    def test_texto_grande_vai_para_quem_aceita(self):
        small, big = Fake("Bing", max_chars=5), Fake("Google", max_chars=100)
        a, _, _ = agg([small, big])
        self.assertEqual(a.translate_batch(["oi", "texto bem maior"], "en", "pt-BR"), ["Bing:oi", "Google:texto bem maior"])
        self.assertEqual(small.calls, 1)

    def test_make_free_ordem_e_ignora_desconhecido(self):
        a = make_free(["yandex", "xxx", "bing", "yandex"])
        self.assertEqual([m.name for m in a.members], ["yandex", "bing"])
        self.assertEqual(len(make_free([]).members), 5)

    def test_assinatura_microsoft_formato(self):
        sig = ms_signature("api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=pt",
                           datetime(2026, 10, 17, 3, 4, 5, tzinfo=timezone.utc), "ab" * 16)
        p = sig.split("::")
        self.assertEqual((p[0], p[2], p[3]), ("MSTranslatorAndroidApp", "Sat, 17 Oct 2026 03:04:05GMT", "ab" * 16))
        self.assertEqual(len(p[1]), 44)


class CopyTests(unittest.TestCase):
    def test_copia_pasta_do_workshop_sem_mexer_na_origem(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ws = d / "workshop" / "123"
            ws.mkdir(parents=True)
            (ws / "Mod X.mod").write_bytes(b"abc")
            (ws / "_ico.png").write_bytes(b"png")
            dest, n = copy_mod_to_game(ws / "Mod X.mod", d / "kenshi")
            self.assertEqual((dest, n), (d / "kenshi" / "mods" / "Mod X", 2))
            self.assertEqual((dest / "Mod X.mod").read_bytes(), b"abc")
            self.assertEqual(sorted(p.name for p in ws.iterdir()), ["Mod X.mod", "_ico.png"])


if __name__ == "__main__":
    unittest.main()
