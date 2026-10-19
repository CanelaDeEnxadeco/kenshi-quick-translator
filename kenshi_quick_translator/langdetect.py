"""
Detecção de idioma do CONTEÚDO de um mod (não do nome do arquivo).

Decide por escrita (cirílico, kana, hangul, han) e, para alfabeto latino, por
palavras muito comuns de cada idioma. É simples de propósito: não depende de
nenhum modelo externo e funciona com textos curtos de diálogo, que é onde
detectores genéricos mais erram.

Duas formas de uso:
- detect_language(textos): UM idioma para um conjunto de textos (o mod todo).
- detect_text(texto): o idioma de UM texto, para mods com mais de um idioma.
  Devolve 'und' quando não dá para ter certeza; nesse caso o serviço de
  tradução é quem detecta (modo "auto").
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

_STOP = {
    "en": "the and you your are is was not that this with for have what but they will would can just don't i'm it's of to in on me my we he she him her do did get go now then there here why how who when from all out".split(),
    "pt": "o a os as um uma de do da dos das em no na nos nas que não nao com para por você voce eu meu minha seu sua é são foi está esta isso mas mais como se ele ela nós vocês já só então aqui ali muito vai vou tem ter fazer".split(),
    "es": "el la los las un una de del en que no con para por tú usted yo mi su es son fue está esto pero más como se él ella nosotros ya solo entonces aquí allí muy va voy tiene tener hacer".split(),
    "fr": "le la les un une de du des en que ne pas avec pour par vous je mon ma son sa est sont était ça mais plus comme se il elle nous déjà seulement alors ici très va vais a avoir faire".split(),
    "de": "der die das ein eine und nicht mit für von du sie ich mein dein ist sind war aber mehr wie er es wir schon nur dann hier sehr geht habe hat haben machen auch".split(),
    "it": "il lo la i gli le un una di del della che non con per da tu voi io mio tuo è sono era ma più come si lui lei noi già solo allora qui molto va ho ha avere fare".split(),
}
NAMES_PT = {
    "en": "Inglês", "zh": "Chinês", "ja": "Japonês", "ko": "Coreano", "ru": "Russo", "uk": "Ucraniano",
    "es": "Espanhol", "fr": "Francês", "de": "Alemão", "it": "Italiano", "pt": "Português",
    "pl": "Polonês", "tr": "Turco", "und": "Indefinido",
}
# Nome de cada idioma no idioma da INTERFACE (pt, en, es, ru, zh). Na tela vem sempre com a sigla: "Português (pt-BR)".
_LN = {
    "en": ("Inglês", "English", "Inglés", "Английский", "英语"),
    "zh": ("Chinês", "Chinese", "Chino", "Китайский", "中文"),
    "ja": ("Japonês", "Japanese", "Japonés", "Японский", "日语"),
    "ko": ("Coreano", "Korean", "Coreano", "Корейский", "韩语"),
    "ru": ("Russo", "Russian", "Ruso", "Русский", "俄语"),
    "uk": ("Ucraniano", "Ukrainian", "Ucraniano", "Украинский", "乌克兰语"),
    "es": ("Espanhol", "Spanish", "Español", "Испанский", "西班牙语"),
    "fr": ("Francês", "French", "Francés", "Французский", "法语"),
    "de": ("Alemão", "German", "Alemán", "Немецкий", "德语"),
    "it": ("Italiano", "Italian", "Italiano", "Итальянский", "意大利语"),
    "pt": ("Português", "Portuguese", "Portugués", "Португальский", "葡萄牙语"),
    "pl": ("Polonês", "Polish", "Polaco", "Польский", "波兰语"),
    "tr": ("Turco", "Turkish", "Turco", "Турецкий", "土耳其语"),
    "und": ("indefinido", "undefined", "indefinido", "не определён", "未确定"),
}
_UI_COL = {"pt": 0, "en": 1, "es": 2, "ru": 3, "zh": 4}
# O detector não separa português do Brasil do de Portugal; o programa é para brasileiros, então "pt" aparece como pt-BR.
_ABBR = {"pt": "pt-BR"}


def lang_name(code: str, ui: str = "pt") -> str:
    """'Português (pt-BR)', 'Portuguese (pt-BR)', 'Inglês (en)'... no idioma da interface. 'und' fica sem sigla."""
    row = _LN.get(code)
    if row is None:
        return code
    name = row[_UI_COL.get(ui, 0)]
    return name if code == "und" else f"{name} ({_ABBR.get(code, code)})"


_TOKEN = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)
_MARKER = re.compile(r"/[A-Z0-9_]{2,}/")


def _script_counts(blob: str) -> Counter[str]:
    scripts: Counter[str] = Counter()
    for ch in blob:
        o = ord(ch)
        if 0x0400 <= o <= 0x04FF:
            scripts["cyr"] += 1
        elif 0x3040 <= o <= 0x30FF:
            scripts["ja"] += 1
        elif 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            scripts["ko"] += 1
        elif 0x4E00 <= o <= 0x9FFF:
            scripts["han"] += 1
        elif ch.isalpha() and o < 0x250:
            scripts["lat"] += 1
    return scripts


def _non_latin_code(top: str, scripts: Counter[str], blob: str) -> str:
    if top == "han":
        return "ja" if scripts["ja"] else "zh"
    if top == "cyr":
        uk = sum(blob.count(c) for c in "іїєґІЇЄҐ")
        return "uk" if uk >= 2 else "ru"
    return top  # 'ja' ou 'ko'


def detect_language(texts: Iterable[str]) -> tuple[str, float]:
    """
    Devolve (codigo, confianca de 0 a 1) para um conjunto de textos. Código
    'und' quando não há texto suficiente para decidir.
    """
    blob = "\n".join(t for t in texts if t)
    if not blob.strip():
        return "und", 0.0

    scripts = _script_counts(blob)
    total = sum(scripts.values())
    if total < 3:
        return "und", 0.0
    top, top_n = scripts.most_common(1)[0]
    share = top_n / total
    if top != "lat":
        return _non_latin_code(top, scripts, blob), min(1.0, share)

    tokens = [t.lower() for t in _TOKEN.findall(blob)]
    if len(tokens) < 4:
        return "und", 0.0
    counts = Counter(tokens)
    scores: dict[str, float] = {}
    for lang, words in _STOP.items():
        wset = set(words)
        hits = sum(c for w, c in counts.items() if w in wset)
        scores[lang] = hits / len(tokens)

    # Letras que só existem em certos idiomas ajudam em textos curtos.
    low = blob.lower()
    for ch, lang, weight in (("ã", "pt", 3), ("õ", "pt", 3), ("ç", "pt", 1), ("ñ", "es", 3), ("¿", "es", 3), ("¡", "es", 3), ("ß", "de", 3)):
        n = low.count(ch)
        if n:
            scores[lang] += weight * n / len(tokens)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, best_score = ranked[0]
    second = ranked[1][1]
    if best_score < 0.08:
        return "und", best_score
    confidence = min(1.0, max(0.0, (best_score - second) / max(best_score, 1e-9)))
    return best, confidence


def detect_text(text: str) -> str:
    """
    Idioma de UM texto: código ('en', 'zh', 'pt'…) ou 'und' se não der para
    ter certeza (texto curto em alfabeto latino, ou mistura de escritas).
    Os marcadores do jogo (/TEAMUP/) não contam.
    """
    clean = _MARKER.sub(" ", text)
    scripts = _script_counts(clean)
    total = sum(scripts.values())
    if total == 0:
        return "und"

    top, top_n = scripts.most_common(1)[0]
    if top != "lat":
        # Chinês com palavras em inglês no meio: dominante, mas misturado -> deixa o serviço decidir.
        if scripts["lat"] / total >= 0.25:
            return "und"
        return _non_latin_code(top, scripts, clean)

    if total - scripts["lat"] > 0:
        return "und"  # latino com outra escrita junto: mistura
    lang, conf = detect_language([clean])
    if lang == "und" or conf < 0.3:
        return "und"
    return lang


def same_language(a: str, b: str) -> bool:
    """'pt' e 'pt-BR' contam como o mesmo idioma."""
    return a.split("-")[0].lower() == b.split("-")[0].lower()
