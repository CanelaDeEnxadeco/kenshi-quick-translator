"""
Serviços com chave para o agregado: IAs no formato OpenAI e Google Cloud v3.

Formatos conferidos na documentação oficial de cada serviço em 17/10/2026
(só LI as páginas; NENHUM serviço foi chamado de verdade aqui, então "não testei"):
- IA: POST {URL base}/chat/completions, cabeçalho "Authorization: Bearer <chave>",
  corpo {"model", "messages"}, resposta em choices[0].message.content.
- Google Cloud v3: POST https://translate.googleapis.com/v3/projects/{projeto}:translateText,
  corpo {contents[], mimeType, sourceLanguageCode, targetLanguageCode}, resposta
  translations[].translatedText. A v3 NÃO aceita chave de API (a documentação diz isso):
  precisa de token OAuth (conta de serviço ou gcloud).
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter

from .freeproviders import Aggregate, DEFAULT_ORDER, FREE_CLASSES, RateLimiter, _http_error, lang_google
from .markers import MARKER_RE
from .providers import DeepL, GoogleCloud, KeyPool, LibreTranslate, Provider, ProviderError, split_keys

# Modelos e endereços abaixo vêm dos exemplos das documentações; mudam com o tempo.
# São só sugestões: todos os campos são editáveis na janela de serviços.
PRESETS: list[dict[str, str]] = [
    {"name": "Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
     "model": "gemini-3.8-flash", "note": "Chave do Google AI Studio. Confira o nome do modelo na documentação."},
    {"name": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-flash",
     "note": "Confira o nome do modelo na documentação do DeepSeek."},
    {"name": "Qwen", "base_url": "https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus",
     "note": "Troque {WorkspaceId} e a região pelo endereço mostrado na SUA conta do Model Studio "
             "(a chave só vale na região em que foi criada)."},
    {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "model": "",
     "note": "Escreva o modelo (lista em openrouter.ai/models)."},
    {"name": "Groq", "base_url": "https://api.groq.com/openai/v1", "model": "",
     "note": "Escreva o modelo (lista na página Models do Groq)."},
    {"name": "Outra IA compatível", "base_url": "", "model": "",
     "note": "Qualquer serviço no formato OpenAI (/chat/completions)."},
]

KINDS: dict[str, str] = {
    "openai": "IA (formato OpenAI)",
    "deepl": "DeepL",
    "google-cloud": "Google Cloud v2 (chave)",
    "google-cloud-v3": "Google Cloud v3 (conta de serviço ou gcloud)",
    "libretranslate": "LibreTranslate",
}

_LANG_EN = {
    "pt-BR": "Brazilian Portuguese", "pt": "European Portuguese", "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "ru": "Russian", "uk": "Ukrainian", "pl": "Polish", "tr": "Turkish",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese",
}

_TOKEN_RE = re.compile(r"ZQ\s*(\d+)\s*ZQ|<\s*x\s*(\d+)\s*/\s*>", re.IGNORECASE)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _signature(text: str) -> tuple[Counter, Counter]:
    """Fichas de proteção e marcadores /ASSIM/ de um texto (para conferir antes/depois)."""
    toks = Counter(m.group(1) or m.group(2) for m in _TOKEN_RE.finditer(text))
    return toks, Counter(MARKER_RE.findall(text))


def _post_json(url: str, body: dict, headers: dict[str, str], timeout: float = 120.0) -> dict:
    """POST JSON sem tentar de novo (o agregado decide). Erros viram ProviderError com status."""
    hdrs = {"Content-Type": "application/json", "User-Agent": "KenshiQuickTranslator/0.4"}
    hdrs.update(headers)
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        err = _http_error(e.code, e.headers.get("Retry-After"))
        err.args = (f"HTTP {e.code}: {detail}" if detail else f"HTTP {e.code}",)
        raise err from e
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        err = ProviderError(f"sem resposta ({type(e).__name__})", retryable=True)
        err.status = 0
        raise err from e
    except ValueError as e:
        raise ProviderError("resposta que não é JSON") from e


# ------------------------------------------------------------------ IA no formato OpenAI
class OpenAICompat(Provider):
    """Qualquer IA que aceite POST {URL base}/chat/completions (Gemini, DeepSeek, Qwen, OpenRouter, Groq...)."""

    needs_key = True
    official = True
    max_batch = 15
    MAX_EXTRA_CALLS = 6  # chamadas extras (dividir lote / refazer texto) por lote

    def __init__(self, base_url: str, api_key: str, model: str, name: str = "IA", rpm: float = 30.0,
                 timeout: float = 120.0) -> None:
        base_url, model, api_key = base_url.strip(), model.strip(), api_key.strip()
        if not base_url or "{" in base_url:
            raise ProviderError(f"{name}: preencha a URL base de verdade (sem {{...}}).")
        if not model:
            raise ProviderError(f"{name}: falta o nome do modelo.")
        if not api_key:
            raise ProviderError(f"{name}: falta a chave.")
        base = base_url.rstrip("/")
        self.url = base if base.endswith("/chat/completions") else base + "/chat/completions"
        self.key, self.model, self.timeout = api_key, model, timeout
        self.short = self.label = name
        self.name = "ia"
        self.limiter = RateLimiter(rpm) if rpm and rpm > 0 else None

    # -- pedido
    def _chat(self, system: str, user: str) -> tuple[str, bool]:
        if self.limiter:
            self.limiter.wait()
        headers = {"Authorization": f"Bearer {self.key}"}
        if "openrouter.ai" in self.url:  # cabeçalho opcional da documentação do OpenRouter
            headers["X-OpenRouter-Title"] = "Kenshi Quick Translator"
        data = _post_json(self.url, {"model": self.model, "stream": False, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}, headers, self.timeout)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError("resposta fora do formato OpenAI") from e
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("resposta vazia", retryable=True)
        return _THINK_RE.sub("", content).strip(), choice.get("finish_reason") == "length"

    def _system(self, source: str, target: str, strict: bool = False) -> str:
        src = "the source language (detect it)" if source == "auto" else _LANG_EN.get(source, source)
        tgt = _LANG_EN.get(target, target)
        s = (
            f"You are a professional video-game localization translator (the game is Kenshi). Translate every string "
            f"from {src} to {tgt}.\n"
            "STRICT RULES:\n"
            "1. Never translate, remove, move or change protected codes: tokens such as ZQ0ZQ, ZQ1ZQ or <x0/>, game "
            "codes in UPPERCASE between slashes such as /TEAMUP/ or /BROTHER/, and anything inside {braces}, [brackets] "
            "or <tags>. Copy them exactly, each one the same number of times.\n"
            "2. Keep punctuation, line breaks and leading/trailing spaces.\n"
            "3. Return ONLY the translation: no explanations, notes, quotes around it or markdown.\n"
            "4. The input is a JSON array of strings. Reply with ONLY a JSON array of strings, with exactly the same "
            "number of items in the same order."
        )
        if strict:
            s += "\nYour previous answer lost or changed a protected code. Copy every protected code exactly."
        return s

    # -- tradução
    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        out: list[str] = list(texts)
        idx = [i for i, t in enumerate(texts) if t.strip()]
        if idx:
            budget = [self.MAX_EXTRA_CALLS]
            got = self._many([texts[i] for i in idx], source, target, budget)
            for i, g in zip(idx, got):
                out[i] = g
        return out

    def _many(self, texts: list[str], source: str, target: str, budget: list[int]) -> list[str]:
        raw, cut = self._chat(self._system(source, target), json.dumps(texts, ensure_ascii=False))
        items = None if cut and len(texts) > 1 else _parse_list(raw, len(texts))
        if items is None:
            if len(texts) == 1:
                return [self._check_one(texts[0], _plain(raw), source, target, budget)]
            if budget[0] <= 0:
                raise ProviderError("a IA não respeitou o formato da resposta", retryable=True)
            budget[0] -= 1
            mid = len(texts) // 2
            return self._many(texts[:mid], source, target, budget) + self._many(texts[mid:], source, target, budget)
        return [self._check_one(s, t, source, target, budget) for s, t in zip(texts, items)]

    def _check_one(self, src: str, out: str, source: str, target: str, budget: list[int]) -> str:
        """Confere códigos do jogo; se mudaram, pede de novo uma vez. A conferência final é do core (markers.py)."""
        if _signature(src) == _signature(out) or budget[0] <= 0:
            return out
        budget[0] -= 1
        raw, _ = self._chat(self._system(source, target, strict=True), json.dumps([src], ensure_ascii=False))
        items = _parse_list(raw, 1)
        return items[0] if items else _plain(raw)


def _parse_list(raw: str, n: int) -> list[str] | None:
    s = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw.strip())
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        data = json.loads(s[i : j + 1])
    except ValueError:
        return None
    if isinstance(data, list) and len(data) == n and all(isinstance(x, str) for x in data):
        return data
    return None


def _plain(raw: str) -> str:
    s = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw.strip()).strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        try:
            v = json.loads(s)
            if isinstance(v, str):
                return v
        except ValueError:
            pass
    return s


# ------------------------------------------------------------------ Google Cloud v3
class GoogleCloudV3(Provider):
    """
    Cloud Translation Advanced (v3), em lote. A v3 não aceita chave de API.

    Login (um dos dois):
    - arquivo JSON de conta de serviço (precisa do pacote 'cryptography': pip install cryptography);
    - gcloud instalado e logado (o programa roda "gcloud auth print-access-token").
    """

    needs_key = True
    official = True
    max_batch = 50
    MAX_CHARS = 25000  # a documentação recomenda menos de 30.000 caracteres por pedido
    SCOPE = "https://www.googleapis.com/auth/cloud-translation"
    HOST = "https://translate.googleapis.com"

    def __init__(self, project: str = "", credentials: str = "", name: str = "Google Cloud v3") -> None:
        self.credentials = credentials.strip().strip('"')
        self.sa: dict | None = None
        if self.credentials:
            try:
                with open(self.credentials, encoding="utf-8") as f:
                    self.sa = json.load(f)
            except (OSError, ValueError) as e:
                raise ProviderError(f"{name}: não consegui ler o arquivo da conta de serviço ({e}).") from e
            project = project.strip() or str(self.sa.get("project_id", ""))
        self.project = project.strip()
        if not self.project:
            raise ProviderError(f"{name}: falta o ID do projeto do Google Cloud.")
        self.short = self.label = name
        self.name = "gcv3"
        self._token = ""
        self._until = 0.0
        self._lock = threading.Lock()

    def _access_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._until:
                return self._token
            self._token, ttl = self._fetch_token()
            self._until = time.time() + max(60.0, ttl - 120.0)
            return self._token

    def _fetch_token(self) -> tuple[str, float]:
        if self.sa is None:
            exe = shutil.which("gcloud")
            if not exe:
                raise ProviderError("Google Cloud v3: não achei o 'gcloud'. Instale-o e faça login, "
                                    "ou indique o arquivo JSON da conta de serviço.")
            kw = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
            try:
                r = subprocess.run([exe, "auth", "print-access-token"], capture_output=True, text=True,
                                   timeout=60, **kw)
            except (OSError, subprocess.TimeoutExpired) as e:
                raise ProviderError(f"Google Cloud v3: o gcloud não respondeu ({e}).") from e
            tok = r.stdout.strip()
            if r.returncode != 0 or not tok:
                raise ProviderError("Google Cloud v3: o gcloud não deu o token. Rode 'gcloud auth login'. "
                                    + r.stderr.strip()[:200])
            return tok, 3000.0
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError as e:
            raise ProviderError("Google Cloud v3 com conta de serviço precisa do pacote 'cryptography' "
                                "(rode: python -m pip install cryptography).") from e
        sa = self.sa
        now = int(time.time())
        aud = sa.get("token_uri") or "https://oauth2.googleapis.com/token"

        def b64(b: bytes) -> bytes:
            return base64.urlsafe_b64encode(b).rstrip(b"=")

        head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claim = b64(json.dumps({"iss": sa["client_email"], "scope": self.SCOPE, "aud": aud,
                                "iat": now, "exp": now + 3600}).encode())
        try:
            key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
            sig = key.sign(head + b"." + claim, padding.PKCS1v15(), hashes.SHA256())
        except (KeyError, ValueError, TypeError) as e:
            raise ProviderError(f"Google Cloud v3: arquivo da conta de serviço inválido ({e}).") from e
        jwt = (head + b"." + claim + b"." + b64(sig)).decode()
        body = ("grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=" + jwt).encode()
        req = urllib.request.Request(aud, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return data["access_token"], float(data.get("expires_in", 3600))
        except urllib.error.HTTPError as e:
            raise ProviderError(f"Google Cloud v3: login recusado (HTTP {e.code}).") from e
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            raise ProviderError(f"Google Cloud v3: falha no login ({type(e).__name__}).", retryable=True) from e

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        out: list[str] = list(texts)
        idx = [i for i, t in enumerate(texts) if t.strip()]
        groups: list[list[int]] = []
        cur: list[int] = []
        size = 0
        for i in idx:
            if cur and (len(cur) >= self.max_batch or size + len(texts[i]) > self.MAX_CHARS):
                groups.append(cur)
                cur, size = [], 0
            cur.append(i)
            size += len(texts[i])
        if cur:
            groups.append(cur)
        url = f"{self.HOST}/v3/projects/{self.project}:translateText"
        for g in groups:
            body = {"contents": [texts[i] for i in g], "mimeType": "text/plain",
                    "targetLanguageCode": lang_google(target)}
            if source != "auto":
                body["sourceLanguageCode"] = lang_google(source)
            data = _post_json(url, body, {"Authorization": f"Bearer {self._access_token()}"}, 60.0)
            try:
                got = [t["translatedText"] for t in data["translations"]]
            except (KeyError, TypeError) as e:
                raise ProviderError("resposta inesperada do Google Cloud v3") from e
            if len(got) != len(g):
                raise ProviderError(f"devolveu {len(got)} textos para {len(g)} enviados", retryable=True)
            for i, t in zip(g, got):
                out[i] = t
        return out


# ------------------------------------------------------------------ montagem
def build_service(e: dict) -> Provider:
    """Cria um serviço a partir de uma entrada de config['services']."""
    kind = e.get("kind", "openai")
    name = (e.get("name") or KINDS.get(kind, kind)).strip()
    ident = str(e.get("id") or name)
    key = str(e.get("api_key", ""))
    keys = split_keys(key)
    rpm = float(e.get("rpm") or 0)
    if kind == "openai":
        if not keys:
            raise ProviderError(f"{name}: falta a chave.")
        ms = [OpenAICompat(e.get("base_url", ""), k, e.get("model", ""), name, rpm) for k in keys]
        p: Provider = ms[0] if len(ms) == 1 else KeyPool(ms)
    elif kind in ("deepl", "google-cloud"):
        cls = DeepL if kind == "deepl" else GoogleCloud
        ms = [cls(k) for k in keys] if keys else [cls("")]
        p = ms[0] if len(ms) == 1 else KeyPool(ms)
    elif kind == "google-cloud-v3":
        p = GoogleCloudV3(str(e.get("project", "")), str(e.get("credentials", "")), name)
    elif kind == "libretranslate":
        p = LibreTranslate(e.get("base_url") or "http://localhost:5000", key)
    else:
        raise ProviderError(f"Tipo de serviço desconhecido: {kind}")
    p.short = name
    p.name = f"svc:{ident}"
    if not isinstance(p, KeyPool):
        p.label = name
    return p


def build_aggregate(services: list[dict] | None, free_order: list[str] | None = None, use_free: bool = True,
                    spread: bool = True) -> Aggregate:
    """Agregado com os serviços configurados (ligados) e, se quiser, os gratuitos como reserva."""
    members: list[Provider] = [build_service(e) for e in (services or []) if e.get("enabled", True)]
    if use_free:
        order: list[str] = []
        for k in (free_order or DEFAULT_ORDER):
            if k in FREE_CLASSES and k not in order:
                order.append(k)
        members += [FREE_CLASSES[k]() for k in (order or DEFAULT_ORDER)]
    return Aggregate(members, spread=spread)
