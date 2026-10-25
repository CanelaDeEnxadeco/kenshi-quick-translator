"""
Quais campos de texto de um mod entram na tradução.

O toolkit só reconhece uma lista fixa de campos (nomes, descrições, diálogos...).
O programa original traduz TODOS os campos de texto, menos os da lista
`translator_blacklist.txt`. Aqui fazemos como o original e acrescentamos uma
proteção a mais para não quebrar o mod:

1. Lista de campos que nunca se traduzem (`translator_blacklist.txt`, os 11 do
   original por padrão; o usuário pode editar).
2. Filtro automático: um campo cujos valores parecem código (nome de arquivo,
   caminho, identificador colado, palavra solta em minúsculas) é deixado em
   inglês, e o programa avisa quais campos deixou de fora.
3. Lista de campos liberados (`translator_liberados.txt`): campos que o
   usuário quer traduzir mesmo que o filtro os ache suspeitos.

Na dúvida o campo NÃO é traduzido: o pior caso é um texto ficar em inglês,
nunca o mod parar de funcionar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from kenshi_translator_toolkit import TranslationUnit, TypeCode, collect
from kenshi_translator_toolkit.format.mod_file import ModFile

BLACKLIST_FILE = "translator_blacklist.txt"
ALLOWLIST_FILE = "translator_liberados.txt"

# Os mesmos 11 campos que o programa original cria por padrão.
DEFAULT_BLACKLIST = (
    "bone name",
    "placeholder",
    "particle system",
    "slave anim",
    "anim name",
    "filenames prefix",
    "carry bone",
    "stringvar",
    "class name",
    "layout exterior",
    "layout interior",
)

_BLACKLIST_HEADER = (
    "# Kenshi Quick Translator: campos que NÃO são traduzidos (um por linha, sem diferenciar maiúsculas).",
    "# Mesma lista padrão do programa original. Linhas com # são comentários.",
    "",
)
_ALLOWLIST_HEADER = (
    "# Kenshi Quick Translator: campos que SEMPRE são traduzidos, mesmo se o filtro automático",
    "# achar que parecem código. Um por linha. Use só se tiver certeza de que é texto para ler.",
    "# (A lista translator_blacklist.txt tem prioridade sobre esta.)",
    "",
)

# Pedaços de nome de campo que indicam algo técnico (animação, arquivo, malha...).
TECH_KEY_HINTS = (
    "bone", "anim", "particle", "file", "path", "mesh", "model", "texture", "sound",
    "sfx", "audio", "icon", "layout", "prefix", "suffix", "class", "stringvar",
    "script", "placeholder", "effect", "skeleton", "material", "shader",
)

_FILE_EXT = re.compile(r"[A-Za-z0-9_\-]\.[A-Za-z0-9]{1,5}$")
_CAMEL = re.compile(r"[a-z][A-Z]")
_LETTER_DIGIT = re.compile(r"[A-Za-z]\d|\d[A-Za-z]")
_TECH_MARK = re.compile(r"[:=;{}\[\]<>|]")


def _read_list(path: Path) -> set[str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return set()
    return {ln.strip().lower() for ln in lines if ln.strip() and not ln.strip().startswith("#")}


def _write_default(path: Path, header: tuple[str, ...], entries: tuple[str, ...] = ()) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join((*header, *entries)) + "\n", encoding="utf-8")
    except OSError:
        pass  # sem permissão para criar: usa só os padrões em memória


@dataclass(frozen=True)
class FieldRules:
    blacklist: frozenset[str] = frozenset(DEFAULT_BLACKLIST)
    allowlist: frozenset[str] = frozenset()

    @classmethod
    def load(cls, folder: str | Path | None = None) -> "FieldRules":
        """Lê as duas listas da pasta de dados; cria os arquivos padrão se não existirem."""
        if folder is None:
            from .config import app_dir

            folder = app_dir()
        folder = Path(folder)
        black, allow = folder / BLACKLIST_FILE, folder / ALLOWLIST_FILE
        if not black.exists():
            _write_default(black, _BLACKLIST_HEADER, DEFAULT_BLACKLIST)
        if not allow.exists():
            _write_default(allow, _ALLOWLIST_HEADER)
        blacklist = _read_list(black) if black.exists() else set(DEFAULT_BLACKLIST)
        return cls(frozenset(blacklist), frozenset(_read_list(allow)))


# ---------------------------------------------------------------- o que parece código
def _token_reason(tok: str) -> str | None:
    """Motivo pelo qual UMA palavra (sem espaços) parece código; None se parece texto."""
    if "/" in tok or "\\" in tok:
        return "caminho"
    if _FILE_EXT.search(tok):
        return "nome de arquivo"
    if "_" in tok:
        return "identificador com _"
    if _CAMEL.search(tok):
        return "identificador (maiúsculas no meio)"
    if _LETTER_DIGIT.search(tok):
        return "identificador com números"
    if _TECH_MARK.search(tok):
        return "código"
    if tok.isalpha() and tok.islower() and len(tok) > 1:
        return "palavra solta em minúsculas"
    return None


def technical_reason(value: str) -> str | None:
    """
    Por que este valor parece código (e não texto para o jogador ler), ou None.
    Valores sem letras não entram aqui: o motor já os ignora.
    """
    v = value.strip()
    if not v or not any(c.isalpha() for c in v):
        return None
    tokens = v.split()
    if len(tokens) == 1:
        return _token_reason(tokens[0])
    reasons = [_token_reason(t) for t in tokens]
    # vários pedaços e TODOS parecem código (ex.: lista de arquivos): é código
    if all(r is not None and r != "palavra solta em minúsculas" for r in reasons):
        return reasons[0]
    return None


# Tipos de registro que carregam texto que o jogador lê (0.7.0). Os outros (animações, arquivos,
# efeitos, malhas...) nunca entram nos campos extras: traduzir ali pode corromper o mod.
# Os 4 extras além dos do toolkit: DIALOGUE, DIALOGUE_LINE, DIALOGUE_PACKAGE e TUTORIAL.
VISIBLE_EXTRA_TYPES = frozenset({
    int(TypeCode.DIALOGUE), int(TypeCode.DIALOGUE_LINE), int(TypeCode.DIALOGUE_PACKAGE), int(TypeCode.TUTORIAL),
})


def is_visible_type(code: int) -> bool:
    """True se o tipo de registro pode ter texto que o jogador vê (diálogos, itens, facções...)."""
    return TypeCode.is_editable(code) or int(code) in VISIBLE_EXTRA_TYPES


def type_label(code: int) -> str:
    try:
        return TypeCode(code).name
    except ValueError:
        return f"TIPO_{int(code)}"


def key_looks_technical(key: str) -> bool:
    k = key.lower()
    return any(h in k for h in TECH_KEY_HINTS)


# ---------------------------------------------------------------- coleta
@dataclass
class SkippedField:
    key: str
    reason: str
    count: int = 0
    example: str = ""


@dataclass
class FieldReport:
    """Campos extras que o filtro automático deixou em inglês (a lista do usuário não entra)."""

    skipped: dict[str, SkippedField] = field(default_factory=dict)
    extra_units: int = 0  # unidades a mais que o toolkit sozinho acharia
    changed_base_units: int = 0  # textos que o mod altera em registros do jogo base (0.6.4)
    technical_types: dict[str, int] = field(default_factory=dict)  # tipo de registro técnico -> textos deixados em inglês (0.7.0)

    def add(self, key: str, reason: str, value: str) -> None:
        s = self.skipped.get(key)
        if s is None:
            s = self.skipped[key] = SkippedField(key, reason, 0, value[:60])
        s.count += 1

    def lines(self, limit: int = 8) -> list[str]:
        items = sorted(self.skipped.values(), key=lambda s: -s.count)
        out = [
            f"«{s.key}»: {s.count} texto(s) deixado(s) em inglês ({s.reason}; ex.: {s.example})"
            for s in items[:limit]
        ]
        if len(items) > limit:
            out.append(f"…e mais {len(items) - limit} campo(s).")
        for name, n in sorted(self.technical_types.items(), key=lambda kv: -kv[1])[:limit]:
            out.append(f"Registros {name}: {n} texto(s) deixado(s) em inglês (tipo técnico, não é texto de jogo)")
        return out


def _is_reference_only(flags: int) -> bool:
    return bool(flags & 0b1) and not bool(flags & 0b10)


def collect_changed_base_units(mod: ModFile, *, index: dict[str, str] | None = None) -> list[TranslationUnit]:
    """
    Textos que o mod ALTERA em registros do jogo base (ou de outro mod): registros "só referência"
    (flag bit 0 ligado, bit 1 desligado) que trazem texto. O toolkit os pula; sem eles, falas e
    descrições trocadas pelo mod ficam no idioma original. O NOME do registro nunca entra
    (renomear um registro do jogo base mudaria o resto do jogo).
    """
    with_text = {r.string_id for r in mod.records if _is_reference_only(r.flags) and r.strings}
    if not with_text:
        return []
    found = collect(mod, include_references=True, include_names=False, index=index)
    return [u for u in found if u.string_id in with_text]


def collect_units(
    mod: ModFile,
    *,
    index: dict[str, str] | None = None,
    rules: FieldRules | None = None,
    extra: bool = True,
    changed_base: bool = True,
    safe_types: bool = True,
) -> tuple[list[TranslationUnit], FieldReport]:
    """
    Unidades do toolkit (campos conhecidos) mais os outros campos de texto que passam
    pela lista e pelo filtro. Com `extra=False` devolve só o que o toolkit acha.
    Com `safe_types=True` (padrão) os campos extras só vêm de tipos de registro que o jogador
    vê (diálogos, itens, facções...); animações, arquivos e efeitos ficam intocados.
    """
    rules = rules or FieldRules()
    report = FieldReport()
    base = collect(mod, index=index)
    if changed_base:
        changed = collect_changed_base_units(mod, index=index)
        base = base + changed
        report.changed_base_units = len(changed)
    if not extra:
        return base, report

    seen = {(u.string_id, u.field) for u in base}
    context = {}
    for u in base:
        context.setdefault(u.string_id, u.context)

    # 1) separa os candidatos por campo para decidir o campo inteiro de uma vez
    cands: dict[str, list[tuple]] = {}
    for rec in mod.records:
        if _is_reference_only(rec.flags):
            continue
        technical = safe_types and not is_visible_type(rec.typecode)
        for key, value in rec.strings:
            if not value or not value.strip() or key.startswith("_"):
                continue
            k = key.strip().lower()
            if k in rules.blacklist or (rec.string_id, key) in seen:
                continue
            if technical:
                label = type_label(rec.typecode)
                report.technical_types[label] = report.technical_types.get(label, 0) + 1
                continue
            cands.setdefault(k, []).append((rec, key, value))
            seen.add((rec.string_id, key))

    extras: list[TranslationUnit] = []
    for k, items in cands.items():
        allowed = k in rules.allowlist
        reasons = [technical_reason(v) for _, _, v in items]
        bad = sum(1 for r in reasons if r)
        hint = key_looks_technical(k)
        key_suspect = not allowed and (hint or bad * 2 >= len(items))
        for (rec, key, value), why in zip(items, reasons):
            if not allowed:
                why_skip = (
                    "nome do campo parece técnico" if hint
                    else (why or ("a maioria dos valores parece código" if key_suspect else None))
                )
                strict = not (TypeCode.is_editable(rec.typecode) or rec.typecode == TypeCode.DIALOGUE_LINE)
                if why_skip is None and strict and len(value.split()) < 2:
                    why_skip = "tipo de registro sem texto conhecido"
                if why_skip is not None:
                    report.add(key, why_skip, value)
                    continue
            extras.append(
                TranslationUnit(
                    string_id=rec.string_id, field=key, source=value, typecode=rec.typecode,
                    record_name=rec.name, context=dict(context.get(rec.string_id, {})),
                )
            )
    report.extra_units = len(extras)
    return base + extras, report
