"""Testes de IA (formato OpenAI), Google Cloud v3 e divisão em paralelo. Servidor FALSO local: nada de internet."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from kenshi_quick_translator.freeproviders import Aggregate
from kenshi_quick_translator.markers import mask
from kenshi_quick_translator.providers import Provider, ProviderError, make_provider
from kenshi_quick_translator.services import GoogleCloudV3, OpenAICompat, build_aggregate


class Server:
    """Responde com o que o teste mandar em self.replies (função: corpo -> (status, dict, headers))."""

    def __init__(self, handler):
        outer = self
        self.requests = []

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n))
                outer.requests.append((self.path, dict(self.headers), body))
                status, data, hdr = handler(body, len(outer.requests))
                raw = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                for k, v in hdr.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def chat(content, finish="stop"):
    return 200, {"choices": [{"message": {"content": content}, "finish_reason": finish}]}, {}


def ai(srv, **kw):
    return OpenAICompat(srv.url + "/v1", "SEGREDO", "modelo-x", "IA teste", rpm=0, **kw)


class OpenAITests(unittest.TestCase):
    def test_formato_pedido_e_resposta(self):
        srv = Server(lambda b, n: chat(json.dumps(["Olá", "Mundo"])))
        self.addCleanup(srv.close)
        out = ai(srv).translate_batch(["Hello", "World"], "en", "pt-BR")
        self.assertEqual(out, ["Olá", "Mundo"])
        path, hdr, body = srv.requests[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(hdr["Authorization"], "Bearer SEGREDO")
        self.assertEqual(body["model"], "modelo-x")
        self.assertEqual(json.loads(body["messages"][1]["content"]), ["Hello", "World"])
        self.assertIn("Brazilian Portuguese", body["messages"][0]["content"])
        self.assertIn("/TEAMUP/", body["messages"][0]["content"])

    def test_cerca_de_codigo_e_resposta_com_think(self):
        srv = Server(lambda b, n: chat("<think>hmm</think>```json\n[\"Oi\"]\n```"))
        self.addCleanup(srv.close)
        self.assertEqual(ai(srv).translate_batch(["Hi"], "en", "pt-BR"), ["Oi"])

    def test_ficha_perdida_pede_de_novo_e_core_confere(self):
        replies = iter([json.dumps(["Vamos ZQ0ZQ"]), json.dumps(["Vamos, ZQ0ZQ!"])])
        srv = Server(lambda b, n: chat(next(replies)))
        self.addCleanup(srv.close)
        # primeira resposta correta: nada de repetir
        self.assertEqual(ai(srv).translate_batch(["Let's ZQ0ZQ"], "en", "pt-BR"), ["Vamos ZQ0ZQ"])
        self.assertEqual(len(srv.requests), 1)
        # resposta que perdeu a ficha: refaz uma vez
        replies2 = iter([json.dumps(["Vamos"]), json.dumps(["Vamos ZQ0ZQ"])])
        srv2 = Server(lambda b, n: chat(next(replies2)))
        self.addCleanup(srv2.close)
        self.assertEqual(ai(srv2).translate_batch(["Let's ZQ0ZQ"], "en", "pt-BR"), ["Vamos ZQ0ZQ"])
        self.assertEqual(len(srv2.requests), 2)
        self.assertIn("lost or changed", srv2.requests[1][2]["messages"][0]["content"])

    def test_marcador_do_jogo_fixo_no_texto(self):
        m = mask("Go /TEAMUP/ now")
        sent = m.text_for("alnum")
        srv = Server(lambda b, n: chat(json.dumps([sent.replace("Go", "Vá").replace("now", "agora")])))
        self.addCleanup(srv.close)
        got = ai(srv).translate_batch([sent], "en", "pt-BR")[0]
        text, problems = m.restore(got, "alnum")
        self.assertEqual((text, problems), ("Vá /TEAMUP/ agora", []))

    def test_quantidade_errada_divide_o_lote(self):
        def handler(body, n):
            items = json.loads(body["messages"][1]["content"])
            if len(items) == 4:
                return chat(json.dumps(["só um"]))
            return chat(json.dumps([f"T:{x}" for x in items]))
        srv = Server(handler)
        self.addCleanup(srv.close)
        out = ai(srv).translate_batch(["a", "b", "c", "d"], "en", "pt-BR")
        self.assertEqual(out, ["T:a", "T:b", "T:c", "T:d"])

    def test_texto_puro_para_um_item(self):
        srv = Server(lambda b, n: chat("Olá!"))
        self.addCleanup(srv.close)
        self.assertEqual(ai(srv).translate_batch(["Hi!"], "en", "pt-BR"), ["Olá!"])

    def test_vazios_nao_vao_ao_servico(self):
        srv = Server(lambda b, n: chat(json.dumps(["Oi"])))
        self.addCleanup(srv.close)
        self.assertEqual(ai(srv).translate_batch(["", "Hi", "  "], "en", "pt-BR"), ["", "Oi", "  "])

    def test_429_leva_status_e_retry_after(self):
        srv = Server(lambda b, n: (429, {"error": "slow down"}, {"Retry-After": "7"}))
        self.addCleanup(srv.close)
        with self.assertRaises(ProviderError) as cm:
            ai(srv).translate_batch(["Hi"], "en", "pt-BR")
        self.assertEqual(cm.exception.status, 429)
        self.assertEqual(cm.exception.retry_after, 7.0)

    def test_campos_obrigatorios(self):
        for args in [("", "k", "m"), ("http://x/{WorkspaceId}", "k", "m"), ("http://x", "k", ""), ("http://x", "", "m")]:
            with self.assertRaises(ProviderError):
                OpenAICompat(*args)


class V3Tests(unittest.TestCase):
    def make(self, srv):
        p = GoogleCloudV3("meu-projeto")
        p.HOST = srv.url
        p._fetch_token = lambda: ("TOKEN123", 3600.0)
        return p

    def test_formato(self):
        srv = Server(lambda b, n: (200, {"translations": [{"translatedText": f"T:{c}"} for c in b["contents"]]}, {}))
        self.addCleanup(srv.close)
        out = self.make(srv).translate_batch(["a", "", "b"], "en", "pt-BR")
        self.assertEqual(out, ["T:a", "", "T:b"])
        path, hdr, body = srv.requests[0]
        self.assertEqual(path, "/v3/projects/meu-projeto:translateText")
        self.assertEqual(hdr["Authorization"], "Bearer TOKEN123")
        self.assertEqual((body["contents"], body["mimeType"], body["sourceLanguageCode"], body["targetLanguageCode"]),
                         (["a", "b"], "text/plain", "en", "pt"))

    def test_divide_por_tamanho(self):
        srv = Server(lambda b, n: (200, {"translations": [{"translatedText": c} for c in b["contents"]]}, {}))
        self.addCleanup(srv.close)
        p = self.make(srv)
        p.MAX_CHARS = 10
        p.translate_batch(["aaaaaa", "bbbbbb", "cc"], "auto", "pt-BR")
        self.assertEqual([r[2]["contents"] for r in srv.requests], [["aaaaaa"], ["bbbbbb", "cc"]])
        self.assertNotIn("sourceLanguageCode", srv.requests[0][2])

    def test_sem_projeto(self):
        with self.assertRaises(ProviderError):
            GoogleCloudV3("")


class Slow(Provider):
    needs_key = True
    max_batch = 5

    def __init__(self, name, fail=False):
        self.name = self.short = self.label = name
        self.fail = fail
        self.threads = set()
        self.calls = 0
        self._l = threading.Lock()

    def translate_batch(self, texts, source, target):
        with self._l:
            self.calls += 1
        if self.fail:
            e = ProviderError("HTTP 429", retryable=True)
            e.status = 429
            raise e
        return [f"{self.name}:{t}" for t in texts]


class SpreadTests(unittest.TestCase):
    def test_divide_lotes_entre_servicos(self):
        a, b, c = Slow("A"), Slow("B"), Slow("C")
        ag = Aggregate([a, b, c], spread=True, sleep=lambda s: None)
        for i in range(6):
            ag.translate_batch([f"t{i}"], "en", "pt-BR")
        self.assertEqual((a.calls, b.calls, c.calls), (2, 2, 2))
        self.assertEqual(ag.parallel_hint, 3)

    def test_sem_spread_mantem_ordem(self):
        a, b = Slow("A"), Slow("B")
        ag = Aggregate([a, b], sleep=lambda s: None)
        for i in range(3):
            ag.translate_batch(["x"], "en", "pt-BR")
        self.assertEqual((a.calls, b.calls), (3, 0))

    def test_falha_vai_para_outro_e_sai_da_rotacao(self):
        a, b = Slow("A", fail=True), Slow("B")
        ev = []
        ag = Aggregate([a, b], spread=True, sleep=lambda s: None, on_event=ev.append)
        outs = [ag.translate_batch(["x"], "en", "pt-BR")[0] for _ in range(4)]
        self.assertTrue(all(o == "B:x" for o in outs))
        self.assertEqual(a.calls, 1)  # entrou em quarentena depois da primeira falha
        self.assertTrue(any("A bloqueou" in m for m in ev))

    def test_max_batch_e_montagem(self):
        srv = Server(lambda b, n: chat(json.dumps(["Oi"])))
        self.addCleanup(srv.close)
        entry = {"id": "g", "kind": "openai", "name": "Gemini", "base_url": srv.url, "api_key": "k1;k2", "model": "m", "rpm": 0}
        ag = build_aggregate([entry, {**entry, "id": "off", "enabled": False}], use_free=True, spread=True)
        self.assertEqual(ag.members[0].short, "Gemini")
        self.assertEqual(ag.members[0].name, "svc:g")
        self.assertEqual(len(ag.members), 1 + 5)  # IA (2 chaves num KeyPool) + 5 gratuitos
        self.assertEqual(ag.max_batch, 10)
        only_ai = build_aggregate([entry], use_free=False)
        self.assertEqual(only_ai.max_batch, 15)
        self.assertEqual(only_ai.translate_batch(["Hi"], "en", "pt-BR"), ["Oi"])
        self.assertIsInstance(make_provider("agregado", services=[entry], use_free=False), Aggregate)

    def test_mensagem_de_modelo_errado(self):
        srv = Server(lambda b, n: (404, {"error": "model not found"}, {}))
        self.addCleanup(srv.close)
        entry = {"id": "g", "kind": "openai", "name": "Gemini", "base_url": srv.url, "api_key": "k", "model": "zzz", "rpm": 0}
        with self.assertRaises(ProviderError) as cm:
            build_aggregate([entry], use_free=False).test()
        self.assertIn("confira modelo/URL", str(cm.exception))


class Etapa3Tests(unittest.TestCase):
    def test_agregado_sem_nada_marcado_da_erro_claro(self):
        with self.assertRaises(ProviderError):
            make_provider("agregado", services=[], use_free=False)

    def test_status_mostra_quarentena(self):
        a, b = Slow("A", fail=True), Slow("B")
        ag = Aggregate([a, b], spread=False, sleep=lambda s: None)
        ag.translate_batch(["x"], "en", "pt-BR")
        st = {name: wait for _k, name, wait in ag.status()}
        self.assertGreater(st["A"], 0)
        self.assertEqual(st["B"], 0)


if __name__ == "__main__":
    unittest.main()
