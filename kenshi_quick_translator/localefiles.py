"""
Arquivos de idioma (.mo) que o mod traz na própria pasta e o pacote do mesmo idioma do jogo.

Achado com o Project Kathun: a pasta `locale` do mod tem um main.mo com ~54 textos em inglês;
com o jogo em português, o menu inteiro caía para o inglês. Aqui o programa:
1) acha os .mo da pasta do mod;
2) acha, na pasta do Kenshi, o .mo do idioma de destino (o do jogo);
3) junta: tudo do jogo + os textos do mod traduzidos para o idioma de destino.

Não sabemos de antemão em qual subpasta o jogo guarda cada idioma, então a busca é por
nome (sigla/nome do idioma no caminho ou no cabeçalho "Language:" do arquivo). Se não achar
com segurança, NADA é alterado e o relatório diz isso.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path

from . import mofile
from .textfiles import translate_strings

MAX_MO_BYTES = 20_000_000
MAX_DEPTH = 6

# Nomes que o idioma costuma ter em caminhos de pastas/arquivos (minúsculo, sem acento).
_NAMES = {
    "en": ["english", "ingles"], "pt": ["portuguese", "portugues", "brazil", "brasil", "brazilian", "brasileiro"],
    "es": ["spanish", "espanol", "castellano"], "fr": ["french", "francais"], "de": ["german", "deutsch"],
    "it": ["italian", "italiano"], "ru": ["russian", "russkij"], "zh": ["chinese", "schinese", "tchinese", "zhongwen"],
    "ja": ["japanese", "nihongo"], "ko": ["korean", "hangugeo"], "pl": ["polish", "polski"], "tr": ["turkish", "turkce"],
    "uk": ["ukrainian"],
}


def _norm(s: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def aliases(code: str) -> set[str]:
    """Jeitos de escrever o idioma: pt-BR -> {'pt-br','pt_br','ptbr','pt','portuguese',...}."""
    c = _norm(code).replace("_", "-")
    base = c.split("-")[0]
    out = {c, c.replace("-", "_"), c.replace("-", ""), base}
    out.update(_NAMES.get(base, []))
    return {a for a in out if a}


def _tokens(text: str) -> set[str]:
    """Pedaços de um caminho/cabeçalho que podem ser nome de idioma (separa por / \\ . _ - espaço)."""
    t = _norm(text)
    parts = set(re.split(r"[\\/.\s]+", t))
    for p in list(parts):
        parts.update(re.split(r"[_\-]+", p))
        parts.add(p.replace("_", "-"))
        parts.add(p.replace("-", "_"))
        parts.add(p.replace("-", "").replace("_", ""))
    return {p for p in parts if p}


def matches_language(path_text: str, header_lang: str, code: str) -> bool:
    al = aliases(code)
    if header_lang and _norm(header_lang).replace("_", "-") in {a.replace("_", "-") for a in al}:
        return True
    return bool(_tokens(path_text) & al)


@dataclass
class ModCatalog:
    path: Path  # caminho completo
    rel: str  # relativo à pasta do mod (com /)
    catalog: mofile.Catalog
    language: str  # do cabeçalho ("" se não diz)


def find_mod_catalogs(folder: str | Path | None) -> list[ModCatalog]:
    """Todos os .mo legíveis da pasta do mod (e subpastas)."""
    out: list[ModCatalog] = []
    if folder is None or not Path(folder).is_dir():
        return out
    root = Path(folder)
    for f in sorted(root.rglob("*.mo")):
        try:
            if len(f.relative_to(root).parts) > MAX_DEPTH or f.stat().st_size > MAX_MO_BYTES:
                continue
            cat = mofile.read_mo(f.read_bytes())
        except (OSError, mofile.MoError):
            continue
        out.append(ModCatalog(f, f.relative_to(root).as_posix(), cat, cat.language))
    return out


def find_game_catalog(kenshi_dir: str | Path | None, target: str, name: str) -> Path | None:
    """
    .mo do idioma de destino na instalação do jogo, com o mesmo nome de arquivo do .mo do mod.
    Procura em data/ e locale/ do Kenshi. Se houver mais de um candidato, vence o de caminho mais
    curto; nada é chutado: sem correspondência de idioma, devolve None.
    """
    if kenshi_dir is None:
        return None
    root = Path(kenshi_dir)
    found: list[tuple[int, Path]] = []
    for sub in ("data", "locale"):
        base = root / sub
        if not base.is_dir():
            continue
        for f in base.rglob(name):
            try:
                rel = f.relative_to(root)
                if len(rel.parts) > MAX_DEPTH + 2 or "mods" in rel.parts or f.stat().st_size > MAX_MO_BYTES:
                    continue
                cat = mofile.read_mo(f.read_bytes())
            except (OSError, mofile.MoError):
                continue
            if matches_language("/".join(rel.parts[:-1]), cat.language, target):
                found.append((len(rel.parts), f))
    if not found:
        return None
    return sorted(found, key=lambda x: (x[0], str(x[1])))[0][1]


@dataclass
class Merged:
    rel: str  # onde instalar, relativo à pasta do mod
    data: bytes
    game_file: Path  # pacote do jogo usado
    mod_texts: int  # textos do mod trazidos
    translated: int  # quantos deles foram traduzidos agora
    game_texts: int  # textos que vieram do jogo


def merge_for_install(
    mod_folder: str | Path | None, kenshi_dir: str | Path | None, provider, target: str, source: str = "en",
    glossary=None, memory=None, cancel: threading.Event | None = None, progress=None,
) -> list[Merged]:
    """
    Um item por .mo do mod para o qual o pacote do jogo foi achado. .mo do mod que já está no
    idioma de destino não precisa de tradução, mas também é juntado (senão esconde o resto do jogo).
    Falhas isoladas (arquivo ilegível, serviço fora) não impedem os outros.
    """
    result: list[Merged] = []
    for mc in find_mod_catalogs(mod_folder):
        if not mc.catalog.entries:
            continue
        game_path = find_game_catalog(kenshi_dir, target, mc.path.name)
        if game_path is None:
            continue
        try:
            game_cat = mofile.read_mo(game_path.read_bytes())
        except (OSError, mofile.MoError):
            continue
        already = bool(mc.language) and matches_language("", mc.language, target)
        texts: dict[str, str] = {}
        if not already and provider is not None:
            # só o msgstr (o que o jogo mostra); msgids de plural/contexto ficam como estão
            values = [v for k, v in mc.catalog.entries.items() if v.strip() and "\x00" not in v]
            done = translate_strings(values, provider, target, source, glossary, memory, cancel, progress, mc.rel)
            for k, v in mc.catalog.entries.items():
                t = done.get(v.strip())
                if t:
                    texts[k] = t
        merged = mofile.merge(game_cat, mc.catalog, texts)
        result.append(Merged(mc.rel, mofile.write_mo(merged), game_path, len(mc.catalog.entries), len(texts),
                             len(game_cat.entries)))
    return result


LOCALE_DIR = "locale"
LOCALE_OFF = "locale_off"


def disable_locale(folder: str | Path | None) -> bool:
    """
    Renomeia a pasta `locale` do mod para `locale_off`, para o jogo não usar o dicionário do mod
    e ficar com o do idioma escolhido (foi o que resolveu o menu em inglês do Project Kathun).
    Nada é apagado. Devolve True se renomeou. Se `locale_off` já existe, não mexe.
    """
    if folder is None:
        return False
    src = Path(folder) / LOCALE_DIR
    dst = Path(folder) / LOCALE_OFF
    try:
        if src.is_dir() and not dst.exists():
            src.rename(dst)
            return True
    except OSError:
        pass
    return False


def enable_locale(folder: str | Path | None) -> bool:
    """Desfaz disable_locale (locale_off -> locale), se `locale` não existir."""
    if folder is None:
        return False
    src = Path(folder) / LOCALE_OFF
    dst = Path(folder) / LOCALE_DIR
    try:
        if src.is_dir() and not dst.exists():
            src.rename(dst)
            return True
    except OSError:
        pass
    return False


# ---------------------------------------------------------------- pacote de idioma dentro do mod
PACK_MARK = ".kenshi-quick-translator"  # arquivo que marca uma pasta locale gerada por este programa
_SKIP_EXT = {".po", ".pot"}
_SKIP_NAMES = {"tips.txt", "namesf.txt", "namesm.txt", "namesmf.txt"}  # o mod tem as próprias listas


def find_game_language_dir(kenshi_dir: str | Path | None, target: str) -> Path | None:
    """Pasta do idioma de destino no jogo (ex.: Kenshi/locale/pt_BR), a que tem mais arquivos .mo/.translation."""
    if kenshi_dir is None:
        return None
    root = Path(kenshi_dir)
    best: tuple[int, Path] | None = None
    for sub in ("locale", "data/locale", "data"):
        base = root / sub
        if not base.is_dir():
            continue
        try:
            dirs = [d for d in base.iterdir() if d.is_dir()]
        except OSError:
            continue
        for d in dirs:
            if not matches_language(d.name, "", target):
                continue
            n = sum(1 for f in d.rglob("*") if f.is_file() and f.suffix.lower() in (".mo", ".translation"))
            if n and (best is None or n > best[0]):
                best = (n, d)
    return best[1] if best else None


def build_locale_pack(
    mod_folder: str | Path | None, kenshi_dir: str | Path | None, provider, target: str, source: str = "en",
    glossary=None, memory=None, cancel: threading.Event | None = None, progress=None,
) -> dict[str, bytes]:
    """
    Quando o mod tem pasta `locale`, o jogo passa a procurar ali TODOS os arquivos de idioma
    (menu, textos do jogo, falas) e não usa mais os dele. Então a `locale` do mod precisa ser o
    pacote do idioma do jogo inteiro, com as frases do mod no lugar. Devolve {caminho: conteúdo}
    relativo à pasta do mod (locale/<idioma>/...). Vazio se o mod não tem .mo ou se o idioma não
    foi achado no jogo (nesse caso nada deve ser mexido).
    """
    mods = [mc for mc in find_mod_catalogs(mod_folder) if mc.catalog.entries]
    original = [mc for mc in mods if mc.rel.startswith("locale_off/")]
    mods = original or mods  # com `locale_off` guardada, o original é ela (a `locale` atual pode ser a gerada antes)
    if not mods:
        return {}
    lang_dir = find_game_language_dir(kenshi_dir, target)
    if lang_dir is None:
        return {}
    texts: dict[str, dict[str, str]] = {}
    for mc in mods:
        t: dict[str, str] = {}
        already = bool(mc.language) and matches_language("", mc.language, target)
        if not already and provider is not None:
            values = [v for v in mc.catalog.entries.values() if v.strip() and "\x00" not in v]
            done = translate_strings(values, provider, target, source, glossary, memory, cancel, progress, mc.rel)
            for k, v in mc.catalog.entries.items():
                x = done.get(v.strip())
                if x:
                    t[k] = x
        texts[mc.path.name.lower()] = (mc, t)  # type: ignore[assignment]
    out: dict[str, bytes] = {}
    base = f"locale/{lang_dir.name}"
    for f in sorted(lang_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() in _SKIP_EXT or f.name.lower() in _SKIP_NAMES:
            continue
        rel = f.relative_to(lang_dir).as_posix()
        data = f.read_bytes()
        hit = texts.get(f.name.lower()) if f.suffix.lower() == ".mo" else None
        if hit is not None:
            mc, t = hit  # type: ignore[misc]
            try:
                game_cat = mofile.read_mo(data)
                data = mofile.write_mo(mofile.merge(game_cat, mc.catalog, t))
            except mofile.MoError:
                pass  # .mo ilegível: copia como está
        out[f"{base}/{rel}"] = data
    out[f"{base}/{PACK_MARK}"] = b"gerado pelo Kenshi Quick Translator\n"
    return out
