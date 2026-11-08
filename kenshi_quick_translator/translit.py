"""
Troca letras de outros alfabetos (russo, grego, japonês, coreano, chinês...) por letras latinas.

Serve para as listas de nomes (namesM/namesF.txt): a fonte do Kenshi só desenha o alfabeto do idioma do
jogo, então nomes em cirílico ou ideogramas num jogo em inglês/português aparecem em branco.
Só mexe numa linha se ela tiver letras que não são latinas e o idioma de destino não usa esse alfabeto.
Cirílico, grego, kana e hangul têm tabela própria; ideogramas chineses/kanji usam o pacote opcional
`unidecode` (se não estiver instalado, essas linhas ficam como estão).
"""
from __future__ import annotations

import unicodedata

try:  # opcional: pinyin dos ideogramas
    from unidecode import unidecode as _unidecode
except Exception:  # noqa: BLE001
    _unidecode = None

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u", "ђ": "dj", "ј": "j", "љ": "lj", "њ": "nj",
    "ћ": "c", "џ": "dz", "ѳ": "f", "ѣ": "e", "ѵ": "i",
}
_GREEK = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l",
    "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f",
    "χ": "ch", "ψ": "ps", "ω": "o",
}
_KANA = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o", "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go", "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo", "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do", "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho", "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po", "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo", "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro", "わ": "wa", "を": "o",
    "ん": "n", "ゔ": "vu", "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
}
_SMALL_Y = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
_HG_L = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
_HG_V = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu",
         "eu", "ui", "i"]
_HG_T = ["", "k", "k", "ks", "n", "nj", "nh", "t", "l", "lk", "lm", "lb", "ls", "lt", "lp", "lh", "m", "p", "ps", "t",
         "t", "ng", "t", "t", "k", "t", "p", "t"]

# alfabeto que cada idioma de destino já usa (nesses, o texto na língua dele não é mexido)
_TARGET_SCRIPTS = {
    "ru": {"cyrillic"}, "uk": {"cyrillic"}, "bg": {"cyrillic"}, "sr": {"cyrillic"}, "be": {"cyrillic"}, "mk": {"cyrillic"},
    "el": {"greek"}, "ja": {"han", "kana"}, "zh": {"han"}, "ko": {"hangul", "han"},
}


def script_of(ch: str) -> str | None:
    """'latin' para letras latinas (com acento também), nome do alfabeto para as outras, None se não é letra."""
    if not ch.isalpha():
        return None
    if ord(ch) < 0x250:
        return "latin"
    name = unicodedata.name(ch, "")
    for key, val in (("LATIN", "latin"), ("CYRILLIC", "cyrillic"), ("GREEK", "greek"), ("HIRAGANA", "kana"),
                     ("KATAKANA", "kana"), ("HANGUL", "hangul"), ("CJK", "han")):
        if name.startswith(key):
            return val
    return "other"


def target_scripts(target_lang: str) -> set[str]:
    return _TARGET_SCRIPTS.get((target_lang or "").lower().replace("_", "-").split("-")[0], set())


def foreign_scripts(text: str, target_lang: str = "en") -> set[str]:
    """Alfabetos não latinos presentes no texto e que o idioma de destino NÃO usa."""
    keep = target_scripts(target_lang)
    return {s for s in (script_of(c) for c in text) if s and s != "latin" and s not in keep}


def _hangul(ch: str) -> str:
    s = ord(ch) - 0xAC00
    return _HG_L[s // 588] + _HG_V[(s % 588) // 28] + _HG_T[s % 28]


def _kana_word(chars: str) -> str:
    out: list[str] = []
    double = False
    for ch in chars:
        o = ord(ch)
        if 0x30A1 <= o <= 0x30F6:  # katakana -> hiragana
            ch = chr(o - 0x60)
        if ch == "ー":  # alongamento: some (Yugo, não Yuugo)
            continue
        if ch == "っ":
            double = True
            continue
        if ch in _SMALL_Y and out:
            prev = out.pop()
            if prev.endswith("i"):
                base = prev[:-1]
                out.append((base if base in ("sh", "ch", "j") else base + "y") + _SMALL_Y[ch])
            else:
                out.append(prev + "y" + _SMALL_Y[ch])
            continue
        r = _KANA.get(ch)
        if r is None:
            out.append(ch)
            continue
        if double:
            r = (r[0] if r[0] != "c" else "t") + r  # kka, ppa, tchi
            double = False
        out.append(r)
    return "".join(out)


def _convert(ch: str, scripts: set[str]) -> str | None:
    sc = script_of(ch)
    if sc is None or sc == "latin" or sc not in scripts:
        return None
    low = ch.lower()
    if sc == "cyrillic":
        return _CYR.get(low)
    if sc == "greek":
        base = "".join(c for c in unicodedata.normalize("NFD", low) if not unicodedata.combining(c))
        return "".join(_GREEK.get(c, c) for c in base)
    if sc == "hangul":
        return _hangul(ch) if 0xAC00 <= ord(ch) <= 0xD7A3 else None
    return None


def latinize_line(line: str, scripts: set[str] | None = None) -> str:
    """Uma linha com letras de outros alfabetos vira letras latinas. Sem nada a trocar, volta igual."""
    scripts = scripts if scripts is not None else {"cyrillic", "greek", "kana", "hangul", "han", "other"}
    if not any((script_of(c) not in (None, "latin")) and script_of(c) in scripts for c in line):
        return line
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        sc = script_of(ch)
        if sc == "kana" and "kana" in scripts:
            j = i
            while j < n and (script_of(line[j]) == "kana" or line[j] in "ーっッ"):
                j += 1
            out.append(_kana_word(line[i:j]).capitalize() if line[i:j] else "")
            i = j
            continue
        if sc in ("han", "other") and sc in scripts and _unidecode is not None:
            j = i
            while j < n and script_of(line[j]) == sc:
                j += 1
            out.append(_unidecode(line[i:j]).strip().title())
            i = j
            continue
        if sc == "hangul" and "hangul" in scripts:  # sílabas de um nome viram uma palavra só: Gimminsu
            j = i
            while j < n and script_of(line[j]) == "hangul":
                j += 1
            out.append("".join(_convert(c, scripts) or c for c in line[i:j]).capitalize())
            i = j
            continue
        if sc == "cyrillic" and "cyrillic" in scripts and line[i:i + 2].lower() == "дж":  # Джон -> John, Джимбад -> Jimbad
            out.append("J" if ch.isupper() else "j")
            i += 2
            continue
        conv = _convert(ch, scripts)
        if conv is None:
            out.append(ch)
        elif ch.isupper():
            nxt = line[i + 1] if i + 1 < n else ""
            out.append(conv.upper() if nxt.isupper() and len(conv) > 0 and script_of(nxt) == sc else conv.capitalize())
        else:
            out.append(conv)
        i += 1
    res = "".join(out)
    return res if any(script_of(c) == "latin" for c in res) else line  # nunca deixa um nome sumir


def latinize_names(raw: bytes, target_lang: str = "en") -> tuple[bytes, int]:
    """
    Converte um arquivo de lista de nomes. Devolve (bytes, quantas linhas mudaram).
    Se nada precisa mudar (já é latino, ou é o alfabeto do idioma de destino), devolve os mesmos bytes.
    """
    enc = "utf-8"
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        enc = "utf-16"
    elif raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError:
        return raw, 0
    scripts = foreign_scripts(text, target_lang)
    if not scripts:
        return raw, 0
    changed = 0
    parts: list[str] = []
    for ln in text.splitlines(keepends=True):
        body = ln.rstrip("\r\n")
        new = latinize_line(body, scripts)
        if new != body:
            changed += 1
        parts.append(new + ln[len(body):])
    if not changed:
        return raw, 0
    return "".join(parts).encode(enc), changed
