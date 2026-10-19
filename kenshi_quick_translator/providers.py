"""
Serviços de tradução.

Todos recebem uma LISTA de textos e devolvem uma lista do mesmo tamanho, sem
juntar frases com separadores (o que faz os tradutores errarem a contagem).
Só usa a biblioteca padrão do Python.

Oficiais, com chave: DeepL, Google Cloud (API v2), LibreTranslate (próprio
servidor ou público). Gratuitos e sem chave (não oficiais, em freeproviders.py):
Google, Google2, Bing, Microsoft, Yandex e o modo Agregado, que junta todos.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

USER_AGENT = "KenshiQuickTranslator/0.1"

# Idiomas oferecidos na interface: código -> nome.
LANGUAGES: dict[str, str] = {
    "auto": "Detectar automaticamente",
    "en": "English",
    "pt-BR": "Português (Brasil)",
    "pt": "Português (Portugal)",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "ru": "Русский",
    "uk": "Українська",
    "pl": "Polski",
    "tr": "Türkçe",
    "ja": "日本語",
    "ko": "한국어",
    "zh": "中文",
}


def friendly_error(msg: str) -> str:
    """Troca erros técnicos compridos (HTML, 429...) por uma frase curta em português."""
    low = msg.lower()
    if "429" in msg or "too many" in low or "<html" in low and "429" in low:
        return ("O serviço bloqueou por excesso de pedidos (erro 429).\n\n"
                "O que fazer: espere alguns minutos e clique em Traduzir de novo (o que já foi traduzido está salvo), "
                "diminua a velocidade, ou use outro serviço / o agregado com mais serviços.")
    if "<html" in low or "<!doctype" in low:
        cut = msg.lower().find("<")
        return msg[:cut].strip() + "\n\n(O serviço devolveu uma página de erro. Tente mais tarde ou troque de serviço.)"
    return msg


class ProviderError(Exception):
    """Falha de um serviço. retryable=True quando vale tentar de novo."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status: int | None = None  # código HTTP, quando houver (0 = sem resposta)
        self.retry_after: float = 0.0  # segundos pedidos pelo serviço (cabeçalho Retry-After)
        self.partial: list | None = None  # o que já foi traduzido antes da falha (uso do agregado)


def _http(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    method: str | None = None,
    timeout: float = 30.0,
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """Requisição HTTP com tentativas e espera crescente em erros temporários."""
    hdrs = {"User-Agent": USER_AGENT}
    hdrs.update(headers or {})
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                sleep(1.5 * (attempt + 1))
                last = e
                continue
            if e.code in (401, 403):
                err = ProviderError(f"Acesso negado ({e.code}). Confira a chave. {body}")
            elif e.code == 456:
                err = ProviderError("Cota do serviço esgotada (456).")
            else:
                err = ProviderError(f"Erro HTTP {e.code}. {body}", retryable=e.code in (429, 500, 502, 503, 504))
            err.status = e.code
            try:
                err.retry_after = float(e.headers.get("Retry-After") or 0)
            except ValueError:
                pass
            raise err from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if attempt < retries - 1:
                sleep(1.5 * (attempt + 1))
                continue
    err = ProviderError(f"Sem conexão com o serviço: {last}", retryable=True)
    err.status = 0
    raise err


class Provider:
    """Interface comum."""

    name = "base"
    label = "base"
    needs_key = False
    official = True
    max_batch = 20
    short = ""  # nome curto nos avisos do agregado
    http_retries = 3  # tentativas de rede (o agregado reduz para 1)

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        raise NotImplementedError

    def test(self) -> str:
        out = self.translate_batch(["Hello, world!"], "en", "pt-BR")
        if not out or not out[0].strip():
            raise ProviderError("O serviço respondeu vazio.")
        return out[0]


# ---------------------------------------------------------------- DeepL
_DEEPL_TARGET = {"pt-BR": "PT-BR", "pt": "PT-PT", "en": "EN-US", "zh": "ZH"}


class DeepL(Provider):
    name = "deepl"
    label = "DeepL (chave)"
    needs_key = True
    max_batch = 50

    def __init__(self, api_key: str) -> None:
        self.key = api_key.strip()
        if not self.key:
            raise ProviderError("Falta a chave do DeepL.")
        host = "api-free.deepl.com" if self.key.endswith(":fx") else "api.deepl.com"
        self.url = f"https://{host}/v2/translate"

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        params: list[tuple[str, str]] = [("text", t) for t in texts]
        params.append(("target_lang", _DEEPL_TARGET.get(target, target.split("-")[0].upper())))
        if source != "auto":
            params.append(("source_lang", source.split("-")[0].upper()))
        params += [("preserve_formatting", "1"), ("split_sentences", "0")]
        raw = _http(
            self.url,
            data=urllib.parse.urlencode(params).encode(),
            headers={"Authorization": f"DeepL-Auth-Key {self.key}"},
            method="POST",
            retries=self.http_retries,
        )
        items = json.loads(raw)["translations"]
        return _check_count(texts, [i["text"] for i in items], self.label)


# ---------------------------------------------------------- Google Cloud v2
class GoogleCloud(Provider):
    name = "google-cloud"
    label = "Google Cloud (chave)"
    needs_key = True
    max_batch = 100

    def __init__(self, api_key: str) -> None:
        self.key = api_key.strip()
        if not self.key:
            raise ProviderError("Falta a chave do Google Cloud.")

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        params: list[tuple[str, str]] = [("q", t) for t in texts]
        params += [("target", target.split("-")[0]), ("format", "text"), ("key", self.key)]
        if source != "auto":
            params.append(("source", source.split("-")[0]))
        raw = _http(
            "https://translation.googleapis.com/language/translate/v2",
            data=urllib.parse.urlencode(params).encode(),
            method="POST",
            retries=self.http_retries,
        )
        items = json.loads(raw)["data"]["translations"]
        return _check_count(texts, [i["translatedText"] for i in items], self.label)


# ------------------------------------------------------------ LibreTranslate
class LibreTranslate(Provider):
    name = "libretranslate"
    label = "LibreTranslate (servidor)"
    needs_key = False
    max_batch = 20

    def __init__(self, url: str = "http://localhost:5000", api_key: str = "") -> None:
        self.url = url.rstrip("/")
        self.key = api_key.strip()

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        body: dict[str, object] = {
            "q": texts,
            "source": "auto" if source == "auto" else source.split("-")[0],
            "target": target.split("-")[0],
            "format": "text",
        }
        if self.key:
            body["api_key"] = self.key
        raw = _http(
            f"{self.url}/translate",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
            retries=self.http_retries,
        )
        out = json.loads(raw).get("translatedText")
        if isinstance(out, str):
            out = [out]
        return _check_count(texts, list(out or []), self.label)


# ------------------------------------------------------------ Simulado (testes)
class Simulated(Provider):
    """Não usa internet. Serve para testar o fluxo e ver o programa funcionando."""

    name = "simulado"
    label = "Simulado (sem internet, só para testar)"
    official = True

    def __init__(self, table: dict[str, str] | None = None, prefix: str = "[PT] ", delay: float = 0.0) -> None:
        self.table = table or {}
        self.prefix = prefix
        self.delay = delay  # segundos por chamada; simula a demora de um serviço de verdade
        self.calls: list[list[str]] = []
        self.sources: list[str] = []  # idioma de origem de cada chamada
        self._lock = threading.Lock()

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        with self._lock:
            self.calls.append(list(texts))
            self.sources.append(source)
        if self.delay:
            time.sleep(self.delay)
        return [self.table.get(t, f"{self.prefix}{t}") for t in texts]


def _check_count(sent: list[str], got: list[str], who: str) -> list[str]:
    if len(sent) != len(got):
        raise ProviderError(f"{who} devolveu {len(got)} textos para {len(sent)} enviados.", retryable=True)
    return got


@dataclass
class ProviderSpec:
    key: str
    label: str
    needs_key: bool
    needs_url: bool = False


SPECS = [
    ProviderSpec("agregado", "Agregado (gratuitos + serviços que você configurar) — recomendado", False),
    ProviderSpec("deepl", DeepL.label, True),
    ProviderSpec("google-cloud", GoogleCloud.label, True),
    ProviderSpec("libretranslate", LibreTranslate.label, False, True),
    ProviderSpec("google-free", "Google (gratuito, não oficial)", False),
    ProviderSpec("google2", "Google2 (gratuito, não oficial)", False),
    ProviderSpec("bing", "Bing (gratuito, não oficial)", False),
    ProviderSpec("microsoft", "Microsoft (gratuito, não oficial)", False),
    ProviderSpec("yandex", "Yandex (gratuito, não oficial)", False),
    ProviderSpec("simulado", Simulated.label, False),
]


class KeyPool(Provider):
    """
    Várias chaves do MESMO serviço agindo como uma só.

    Reparte os lotes entre as chaves, uma de cada vez (rodízio), para que o
    limite de pedidos de cada conta renda junto. Se uma chave falhar (cota
    esgotada, acesso negado), o lote vai para a próxima; uma chave que falha
    várias vezes seguidas é deixada de lado até as outras também falharem.
    """

    SKIP_AFTER = 3

    def __init__(self, members: list[Provider]) -> None:
        if len(members) < 2:
            raise ValueError("KeyPool precisa de pelo menos duas chaves")
        self.members = members
        first = members[0]
        self.name = first.name
        self.label = f"{first.label} · {len(members)} chaves"
        self.needs_key = first.needs_key
        self.official = first.official
        self.max_batch = min(m.max_batch for m in members)
        self._next = 0
        self._bad = [0] * len(members)
        self._lock = threading.Lock()

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        with self._lock:
            start = self._next
            self._next = (self._next + 1) % len(self.members)
            order = [(start + k) % len(self.members) for k in range(len(self.members))]
            alive = [i for i in order if self._bad[i] < self.SKIP_AFTER]
            order = alive or order  # se todas estão mal, tenta todas mesmo assim
        last: ProviderError | None = None
        for i in order:
            try:
                out = self.members[i].translate_batch(texts, source, target)
            except ProviderError as e:
                last = e
                with self._lock:
                    self._bad[i] += 1
                continue
            with self._lock:
                self._bad[i] = 0
            return out
        assert last is not None
        raise last

    def test(self) -> str:
        """Testa cada chave e diz qual falhou, em vez de só 'uma delas'."""
        results, errors = [], []
        for n, m in enumerate(self.members, 1):
            try:
                results.append(m.test())
            except ProviderError as e:
                errors.append(f"chave {n}: {e}")
        if errors:
            raise ProviderError("; ".join(errors))
        return results[0]


def split_keys(api_key: str) -> list[str]:
    """Separa várias chaves digitadas com ';' ou uma por linha."""
    parts = api_key.replace("\r", "\n").replace(";", "\n").split("\n")
    seen: list[str] = []
    for p in (x.strip() for x in parts):
        if p and p not in seen:
            seen.append(p)
    return seen


def make_provider(key: str, api_key: str = "", url: str = "", free_order: list[str] | None = None,
                  services: list[dict] | None = None, use_free: bool = True, spread: bool = False) -> Provider:
    if key in ("deepl", "google-cloud"):
        cls = DeepL if key == "deepl" else GoogleCloud
        keys = split_keys(api_key)
        if len(keys) > 1:
            return KeyPool([cls(k) for k in keys])
        return cls(keys[0] if keys else "")
    if key == "libretranslate":
        return LibreTranslate(url or "http://localhost:5000", api_key)
    if key == "agregado" and (services or not use_free):
        from .services import build_aggregate

        return build_aggregate(services, free_order, use_free, spread)
    if key == "agregado" or key in ("google-free", "google2", "bing", "microsoft", "yandex"):
        from .freeproviders import make_free

        return make_free(free_order if key == "agregado" else [key], spread=spread and key == "agregado")
    if key == "simulado":
        return Simulated()
    raise ValueError(f"Serviço desconhecido: {key}")
