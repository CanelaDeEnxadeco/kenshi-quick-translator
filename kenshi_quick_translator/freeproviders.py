"""
Serviços gratuitos, sem chave, e o modo AGREGADO.

Os cinco serviços (Google, Google2, Bing, Microsoft, Yandex) são reescritos em
Python a partir da biblioteca aberta GTranslate (d4n3436/GTranslate, MIT), que é
a mesma usada pelo KenshiTranslator original (Kakrain, MIT). Todos são
endpoints NÃO oficiais: podem limitar ou mudar a qualquer momento.

O Agregado tenta os serviços em ordem; se um falha (429, 503, tempo esgotado,
bloqueio), o resto do lote vai para o próximo e o serviço que falhou sai da
rotação por alguns minutos (cada nova falha seguida dobra o tempo). Só desiste
quando TODOS falham, depois de esperar e tentar de novo algumas vezes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.cookiejar
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Callable

from .providers import Provider, ProviderError

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


# ------------------------------------------------------------------ utilitários
class RateLimiter:
    """Garante um intervalo mínimo entre pedidos (vale para todas as threads)."""

    def __init__(self, per_minute: float, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.interval = 60.0 / max(1.0, per_minute)
        self._next = 0.0
        self._lock = threading.Lock()
        self._sleep = sleep
        self._clock = clock

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            self._sleep(start - now)


class TooLong(Exception):
    """Texto maior do que o serviço aceita; não é falha do serviço, só passa para outro."""


class _Web:
    """Um pedido HTTP por vez, SEM tentar de novo (quem decide é o agregado). Guarda cookies."""

    def __init__(self, user_agent: str = BROWSER_UA, timeout: float = 20.0) -> None:
        self.ua = user_agent
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
        hdrs = {"User-Agent": self.ua}
        hdrs.update(headers or {})
        req = urllib.request.Request(url, data=data, headers=hdrs)
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise _http_error(e.code, e.headers.get("Retry-After")) from e
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            err = ProviderError(f"sem resposta ({type(e).__name__})", retryable=True)
            err.status = 0
            raise err from e


def _http_error(code: int, retry_after: str | None = None) -> ProviderError:
    err = ProviderError(f"HTTP {code}", retryable=code in (429, 500, 502, 503, 504))
    err.status = code
    try:
        err.retry_after = float(retry_after) if retry_after else 0.0
    except ValueError:
        err.retry_after = 0.0
    return err


# ------------------------------------------------------------------ códigos de idioma
def _base(code: str) -> str:
    return code.split("-")[0]


def lang_google(code: str) -> str:
    return {"pt-BR": "pt", "pt": "pt-PT", "zh": "zh-CN", "auto": "auto"}.get(code, _base(code))


def lang_microsoft(code: str) -> str:  # Bing e Microsoft usam os mesmos códigos
    return {"pt-BR": "pt", "pt": "pt-pt", "zh": "zh-Hans"}.get(code, _base(code))


def lang_yandex(code: str) -> str:
    return {"pt-BR": "pt-BR", "pt": "pt", "zh": "zh"}.get(code, _base(code))


# ------------------------------------------------------------------ base dos serviços
class FreeService(Provider):
    """Um serviço gratuito. Traduz texto a texto (como a GTranslate faz)."""

    short = "?"
    needs_key = False
    official = False
    max_batch = 10
    rpm = 60  # pedidos por minuto que NÓS nos permitimos (valor prudente, não um limite oficial)
    max_chars = 1000

    def __init__(self, rpm: float | None = None) -> None:
        self.web = _Web()
        self.limiter = RateLimiter(rpm or self.rpm)

    def _one(self, text: str, source: str, target: str) -> str:
        raise NotImplementedError

    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str | None]:
        out: list[str | None] = []
        for t in texts:
            if not t.strip():
                out.append(t)
                continue
            if len(t) > self.max_chars:
                out.append(None)  # fica para outro serviço
                continue
            self.limiter.wait()
            try:
                res = self._one(t, source, target)
            except ProviderError as e:
                e.partial = out
                raise
            except (ValueError, KeyError, IndexError, TypeError) as e:
                err = ProviderError(f"resposta inesperada ({type(e).__name__})")
                err.partial = out
                raise err from e
            if not res.strip():
                err = ProviderError("resposta vazia")
                err.partial = out
                raise err
            out.append(res)
        return out


# ------------------------------------------------------------------ Google
class Google(FreeService):
    name = "google-free"
    short = "Google"
    label = "Google (gratuito, não oficial)"
    rpm = 120
    max_chars = 4000

    def _one(self, text: str, source: str, target: str) -> str:
        params = {"client": "gtx", "sl": lang_google(source), "tl": lang_google(target), "dt": "t", "dj": "1", "source": "input"}
        url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
        body = urllib.parse.urlencode({"q": text}).encode()
        data = json.loads(self.web.request(url, body, {"Content-Type": "application/x-www-form-urlencoded"}))
        return "".join(s.get("trans", "") for s in data.get("sentences", []) if "trans" in s)


class Google2(FreeService):
    """Interface 'batchexecute' do site translate.google.com (outro caminho, outro limite)."""

    name = "google2"
    short = "Google2"
    label = "Google2 (gratuito, não oficial)"
    rpm = 90
    max_chars = 4500
    RPC = "MkEWBc"

    def _one(self, text: str, source: str, target: str) -> str:
        payload = json.dumps([[text, lang_google(source), lang_google(target), 1], []], ensure_ascii=False, separators=(",", ":"))
        freq = json.dumps([[[self.RPC, payload, None, "generic"]]], ensure_ascii=False, separators=(",", ":"))
        url = f"https://translate.google.com/_/TranslateWebserverUi/data/batchexecute?rpcids={self.RPC}"
        raw = self.web.request(url, urllib.parse.urlencode({"f.req": freq}).encode(),
                               {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}).decode("utf-8")
        outer, _ = json.JSONDecoder().raw_decode(raw[raw.index("[") :])  # pula o prefixo )]}'
        root = json.loads(outer[0][2])
        first = root[1][0][0]
        if len(first) > 5 and isinstance(first[5], list):
            return " ".join(x[0] for x in first[5])
        return first[0]


# ------------------------------------------------------------------ Bing
class Bing(FreeService):
    name = "bing"
    short = "Bing"
    label = "Bing (gratuito, não oficial)"
    rpm = 60
    max_chars = 1000
    HOST = "https://www.bing.com"
    IID = "translator.5024.1"
    START = 'var params_AbusePreventionHelper = ['

    def __init__(self, rpm: float | None = None) -> None:
        super().__init__(rpm)
        self._cred: tuple[str, str, str] | None = None  # (token, key, ig)
        self._cred_until = 0.0
        self._cred_lock = threading.Lock()

    def _credentials(self) -> tuple[str, str, str]:
        with self._cred_lock:
            if self._cred and time.time() < self._cred_until:
                return self._cred
            html = self.web.request(f"{self.HOST}/translator").decode("utf-8", "replace")
            i = html.find(self.START)
            if i < 0:
                raise ProviderError("não achei as credenciais do Bing (página mudou ou foi bloqueada)")
            i += len(self.START)
            j = html.index(",", i)
            key = html[i:j]
            k = j + 2  # pula ,"
            token = html[k : html.index('"', k)]
            self._cred = (token, key, uuid.uuid4().hex.upper())
            self._cred_until = time.time() + 55 * 60  # a credencial vale 1 hora
            return self._cred

    def _one(self, text: str, source: str, target: str) -> str:
        token, key, ig = self._credentials()
        data = {"fromLang": "auto-detect" if source == "auto" else lang_microsoft(source), "text": text,
                "to": lang_microsoft(target), "token": token, "key": key}
        url = f"{self.HOST}/ttranslatev3?isVertical=1&IG={ig}&IID={self.IID}"
        try:
            res = json.loads(self.web.request(url, urllib.parse.urlencode(data).encode(),
                                              {"Content-Type": "application/x-www-form-urlencoded"}))
        except ProviderError:
            self._cred = None  # na dúvida, pega credencial nova na próxima
            raise
        if isinstance(res, dict) and "statusCode" in res:  # o Bing responde 200 mesmo com erro
            raise _http_error(int(res.get("statusCode") or 0))
        return res[0]["translations"][0]["text"]


# ------------------------------------------------------------------ Microsoft
# Chave do app Android do Microsoft Translator, como na GTranslate (MIT).
_MS_KEY = bytes([
    0xa2, 0x29, 0x3a, 0x3d, 0xd0, 0xdd, 0x32, 0x73, 0x97, 0x7a, 0x64, 0xdb, 0xc2, 0xf3, 0x27, 0xf5,
    0xd7, 0xbf, 0x87, 0xd9, 0x45, 0x9d, 0xf0, 0x5a, 0x09, 0x66, 0xc6, 0x30, 0xc6, 0x6a, 0xaa, 0x84,
    0x9a, 0x41, 0xaa, 0x94, 0x3a, 0xa8, 0xd5, 0x1a, 0x6e, 0x4d, 0xaa, 0xc9, 0xa3, 0x70, 0x12, 0x35,
    0xc7, 0xeb, 0x12, 0xf6, 0xe8, 0x23, 0x07, 0x9e, 0x47, 0x10, 0x95, 0x91, 0x88, 0x55, 0xd8, 0x17,
])
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def ms_signature(url: str, now: datetime | None = None, guid: str | None = None) -> str:
    """X-MT-Signature: HMAC-SHA256 de 'MSTranslatorAndroidApp'+url escapada+data+guid (minúsculas)."""
    now = now or datetime.now(timezone.utc)
    guid = guid or uuid.uuid4().hex
    stamp = f"{_DAYS[now.weekday()]}, {now.day:02d} {_MONTHS[now.month - 1]} {now.year} {now:%H:%M:%S}GMT"
    msg = f"MSTranslatorAndroidApp{urllib.parse.quote(url, safe='')}{stamp}{guid}".lower().encode()
    digest = base64.b64encode(hmac.new(_MS_KEY, msg, hashlib.sha256).digest()).decode()
    return f"MSTranslatorAndroidApp::{digest}::{stamp}::{guid}"


class Microsoft(FreeService):
    name = "microsoft"
    short = "Microsoft"
    label = "Microsoft (gratuito, não oficial)"
    rpm = 90
    max_chars = 1000

    def _one(self, text: str, source: str, target: str) -> str:
        url = f"api.cognitive.microsofttranslator.com/translate?api-version=3.0&to={lang_microsoft(target)}"
        if source != "auto":
            url += f"&from={lang_microsoft(source)}"
        body = json.dumps([{"Text": text}], ensure_ascii=False).encode()
        res = json.loads(self.web.request(f"https://{url}", body, {
            "Content-Type": "application/json", "X-MT-Signature": ms_signature(url)}))
        return res[0]["translations"][0]["text"]


# ------------------------------------------------------------------ Yandex
class Yandex(FreeService):
    name = "yandex"
    short = "Yandex"
    label = "Yandex (gratuito, não oficial)"
    rpm = 90
    max_chars = 3000
    API = "https://translate.yandex.net/api/v1/tr.json"

    def __init__(self, rpm: float | None = None) -> None:
        super().__init__(rpm)
        self.web = _Web("ru.yandex.translate/3.20.2024")
        self._ucid = uuid.uuid4().hex
        self._ucid_at = time.time()

    def _one(self, text: str, source: str, target: str) -> str:
        if time.time() - self._ucid_at > 360:  # a GTranslate troca o id a cada 6 minutos
            self._ucid, self._ucid_at = uuid.uuid4().hex, time.time()
        lang = lang_yandex(target) if source == "auto" else f"{lang_yandex(source)}-{lang_yandex(target)}"
        url = f"{self.API}/translate?ucid={self._ucid}&srv=android&format=text"
        try:
            raw = self.web.request(url, urllib.parse.urlencode({"text": text, "lang": lang}).encode(),
                                   {"Content-Type": "application/x-www-form-urlencoded"})
        except ProviderError:
            raise
        res = json.loads(raw)
        if res.get("code") != 200:
            raise _http_error(int(res.get("code") or 0))
        return "".join(res["text"])


FREE_CLASSES: dict[str, type[FreeService]] = {
    "google-free": Google, "google2": Google2, "bing": Bing, "microsoft": Microsoft, "yandex": Yandex,
}
DEFAULT_ORDER = ["google-free", "bing", "microsoft", "yandex", "google2"]


# ------------------------------------------------------------------ agregado
def _s(m: Provider) -> str:
    return getattr(m, "short", "") or m.label


def _single_try(m: Provider) -> None:
    """Dentro do agregado quem decide tentar de novo é ele: serviços com chave fazem 1 tentativa só."""
    m.http_retries = 1
    for sub in getattr(m, "members", []) or []:
        _single_try(sub)


def _reason(e: ProviderError) -> str:
    st = getattr(e, "status", None)
    if st == 429:
        return "bloqueou (muitos pedidos)"
    if st in (401, 403):
        return "recusou o acesso (confira a chave)"
    if st in (400, 404, 422):
        return f"não aceitou o pedido (confira modelo/URL): {str(e)[:120]}"
    if st == 0 or st in (500, 502, 503, 504):
        return "não respondeu"
    return f"falhou ({e})"


def _fmt_wait(seconds: float) -> str:
    return f"{round(seconds / 60)} min" if seconds >= 90 else f"{round(seconds)} s"


class Aggregate(Provider):
    """Tenta os serviços em ordem; o que falha sai da rotação por um tempo; só desiste se TODOS falham."""

    name = "agregado"
    needs_key = False
    official = False
    max_batch = 10
    COOL_BASE = 60.0
    COOL_MAX = 600.0
    MAX_ROUNDS = 4
    MAX_WAIT = 60.0

    def __init__(self, members: list[Provider], on_event: Callable[[str], None] | None = None,
                 sleep: Callable[[float], None] | None = None, clock: Callable[[], float] = time.monotonic,
                 spread: bool = False) -> None:
        if not members:
            raise ProviderError("Escolha pelo menos um serviço para o agregado.")
        self.members = members
        self.spread = spread  # True: cada lote começa por um serviço diferente (divide o trabalho em paralelo)
        self._rr = 0
        self.max_batch = min(getattr(m, "max_batch", 10) for m in members)
        self.parallel_hint = len(members) if spread else 0
        for m in members:
            _single_try(m)
        self.label = "Agregado: " + " → ".join(_s(m) for m in members)
        self.on_event = on_event
        self._clock = clock
        self._cancel: threading.Event | None = None
        self._sleep = sleep
        self._until: dict[str, float] = {}
        self._why: dict[str, str] = {}  # último motivo de bloqueio de cada serviço (para a tela)
        self._strikes: dict[str, int] = {}
        self._lock = threading.Lock()

    # -- ligações com o resto do programa
    def bind_cancel(self, ev: threading.Event) -> None:
        self._cancel = ev

    def _pause(self, seconds: float) -> None:
        if self._sleep:
            self._sleep(seconds)
        elif self._cancel is not None:
            if self._cancel.wait(seconds):
                raise ProviderError("Cancelado.")
        else:
            time.sleep(seconds)

    def _emit(self, msg: str) -> None:
        if self.on_event:
            self.on_event(msg)

    # -- estado dos serviços
    def _cooling(self, m: Provider) -> float:
        with self._lock:
            return max(0.0, self._until.get(m.name, 0.0) - self._clock())

    def status(self) -> list[tuple[str, str, float]]:
        """(chave, nome, segundos que faltam para voltar; 0 = ativo)."""
        return [(m.name, _s(m), self._cooling(m)) for m in self.members]

    def status_detail(self) -> list[dict]:
        """Como status(), com mais dados para a tela: falhas seguidas e o último motivo."""
        waits = {m.name: self._cooling(m) for m in self.members}  # _cooling usa o mesmo lock: fora dele
        with self._lock:
            return [{"key": m.name, "name": _s(m), "wait": waits[m.name],
                     "strikes": self._strikes.get(m.name, 0), "why": self._why.get(m.name, "")}
                    for m in self.members]

    def _penalize(self, m: Provider, e: ProviderError) -> None:
        with self._lock:
            self._why[m.name] = _reason(e)
            was_cooling = self._until.get(m.name, 0.0) > self._clock()
            n = self._strikes.get(m.name, 0) + 1
            self._strikes[m.name] = n
            wait = max(min(self.COOL_BASE * 2 ** (n - 1), self.COOL_MAX), float(getattr(e, "retry_after", 0) or 0))
            self._until[m.name] = max(self._until.get(m.name, 0.0), self._clock() + wait)
        if was_cooling:
            return
        nxt = next((x for x in self.members if x is not m and not self._cooling(x)), None)
        msg = f"{_s(m)} {_reason(e)}. Fica de fora por {_fmt_wait(wait)}."
        self._emit(msg + (f" Passei para o {nxt.short}." if nxt else " Sem outro serviço livre agora; vou esperar."))

    def _ok(self, m: Provider) -> None:
        with self._lock:
            self._strikes[m.name] = 0
            self._why.pop(m.name, None)

    def _order(self) -> list[Provider]:
        """Ordem de tentativa. Com spread, começa por um serviço livre diferente a cada lote."""
        if not self.spread or len(self.members) < 2:
            return self.members
        with self._lock:
            n = len(self.members)
            start = self._rr % n
            self._rr += 1
        rot = self.members[start:] + self.members[:start]
        return [m for m in rot if not self._cooling(m)] + [m for m in rot if self._cooling(m)]

    # -- tradução
    def translate_batch(self, texts: list[str], source: str, target: str) -> list[str]:
        result: list[str | None] = [None] * len(texts)
        pending = list(range(len(texts)))
        errors: list[str] = []
        for _round in range(self.MAX_ROUNDS):
            tried = False
            for m in self._order():
                if not pending:
                    break
                if self._cooling(m):
                    continue
                tried = True
                sent = list(pending)
                got: list[str | None] = []
                err: ProviderError | None = None
                try:
                    got = m.translate_batch([texts[i] for i in sent], source, target)
                except ProviderError as e:
                    err = e
                    got = list(getattr(e, "partial", None) or [])
                for idx, val in zip(sent, got):
                    if val is not None:
                        result[idx] = val
                if any(v is not None for v in got):
                    self._ok(m)
                pending = [i for i in pending if result[i] is None]
                if err is not None:
                    errors.append(f"{_s(m)}: {err}")
                    self._penalize(m, err)
            if not pending:
                return [r or "" for r in result]
            if tried and not errors:
                raise ProviderError("Há textos grandes demais para os serviços escolhidos.")
            waits = [self._cooling(m) for m in self.members]
            waits = [w for w in waits if w > 0]
            wait = min(max(min(waits) if waits else 5.0, 3.0), self.MAX_WAIT)
            self._emit(f"Todos os serviços estão ocupados. Espero {_fmt_wait(wait)} e tento de novo.")
            self._pause(wait)
        raise ProviderError("Todos os serviços falharam: " + "; ".join(errors[-len(self.members):]))

    def test(self) -> str:
        """Testa cada serviço (ignora a quarentena) e diz o resultado de cada um, em português."""
        lines, ok = [], 0
        for m in self.members:
            try:
                txt = m.test()
                lines.append(f"✓ {_s(m)}: {txt}")
                ok += 1
            except ProviderError as e:
                lines.append(f"✗ {_s(m)} {_reason(e)}")
        if not ok:
            raise ProviderError("Nenhum serviço respondeu.\n" + "\n".join(lines))
        return "\n".join(lines)


def make_free(keys: list[str] | None, spread: bool = False) -> Aggregate:
    """Monta o agregado na ordem dada (chaves desconhecidas são ignoradas; vazio = ordem padrão)."""
    order = [k for k in (keys or []) if k in FREE_CLASSES] or DEFAULT_ORDER
    seen: list[str] = []
    for k in order:
        if k not in seen:
            seen.append(k)
    return Aggregate([FREE_CLASSES[k]() for k in seen], spread=spread)
