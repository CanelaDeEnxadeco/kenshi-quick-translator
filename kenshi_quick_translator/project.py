"""
Projeto de tradução de UM mod.

Guarda em um arquivo JSON cada texto do mod, a tradução e o estado de
revisão. Assim, reabrir o programa, procurar mods de novo ou atualizar o mod
original nunca joga fora o trabalho já feito.
"""

from __future__ import annotations

import hashlib
import os
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from kenshi_translator_toolkit import ModFile, TranslationUnit, apply_po, collect, dump, load, to_po

from .fields import FieldReport, FieldRules, collect_units
from .locate import real_mod_name

PENDING = "pendente"
AUTO = "automatica"
REVIEWED = "revisada"
ATTENTION = "atencao"
IGNORED = "ignorada"
STATUSES = (PENDING, AUTO, REVIEWED, ATTENTION, IGNORED)

FORMAT_VERSION = 1
_SAVE_LOCK = threading.Lock()


@dataclass
class Unit:
    string_id: str
    field: str
    source: str
    typecode: int
    record_name: str
    translation: str = ""
    status: str = PENDING
    note: str = ""
    context: dict[str, str] = field(default_factory=dict)
    lang: str = ""  # idioma detectado deste texto (só preenchido no modo "vários idiomas")

    @property
    def key(self) -> tuple[str, str]:
        return (self.string_id, self.field)

    def to_toolkit(self) -> TranslationUnit:
        return TranslationUnit(
            string_id=self.string_id,
            field=self.field,
            source=self.source,
            typecode=self.typecode,
            record_name=self.record_name,
            translation=self.translation,
            context=dict(self.context),
        )


def _replace_with_retry(tmp: Path, target: Path, text: str, tries: int = 12, wait: float = 0.25) -> None:
    """
    tmp -> target. No Windows, antivírus, sincronizadores de nuvem ou outra cópia do programa podem
    segurar o arquivo por instantes ("Acesso negado", WinError 5): tenta de novo algumas vezes.
    Se não adiantar, grava direto no arquivo (menos seguro, mas não perde o trabalho).
    """
    last: OSError | None = None
    for i in range(tries):
        try:
            tmp.replace(target)
            return
        except PermissionError as e:
            last = e
            time.sleep(wait)
    try:
        try:
            os.chmod(target, 0o666)  # tira o "somente leitura", se for isso
        except OSError:
            pass
        target.write_text(text, encoding="utf-8")
        try:
            tmp.unlink()
        except OSError:
            pass
    except OSError:
        raise last or PermissionError(f"não consegui gravar {target}")


@dataclass
class Project:
    mod_name: str  # nome do arquivo, com extensão (ex.: "recruit Saelith.mod")
    mod_sha1: str
    source_lang: str = "auto"
    target_lang: str = "pt-BR"
    units: list[Unit] = field(default_factory=list)
    path: Path | None = None  # onde o projeto é salvo
    mod_path: str = ""  # caminho completo do mod dono deste projeto (distingue mods de mesmo nome)
    field_report: FieldReport | None = field(default=None, repr=False, compare=False)  # campos deixados em inglês pelo filtro (só em memória)

    # ------------------------------------------------------------ criação
    @classmethod
    def from_mod_file(
        cls,
        mod_path: str | Path,
        workdir: str | Path,
        target_lang: str = "pt-BR",
        source_lang: str = "auto",
        index: dict[str, str] | None = None,
        rules: FieldRules | None = None,
        safe_types: bool = True,
    ) -> "Project":
        """
        Lê o mod e cria (ou atualiza) o projeto. Se já existir projeto salvo,
        mantém as traduções cujo texto original não mudou.
        """
        mod_path = Path(mod_path)
        raw = mod_path.read_bytes()
        mod = load(raw)
        if rules is None:  # listas de campos ficam na pasta de dados (a dos projetos fica dentro dela)
            rules = FieldRules.load(Path(workdir).parent)
        found, field_report = collect_units(mod, index=index, rules=rules, safe_types=safe_types)
        fresh = [
            Unit(
                string_id=u.string_id, field=u.field, source=u.source,
                typecode=u.typecode, record_name=u.record_name, context=dict(u.context),
            )
            for u in found
        ]
        proj = cls(
            mod_name=real_mod_name(mod_path.name),
            mod_sha1=hashlib.sha1(raw).hexdigest(),
            source_lang=source_lang,
            target_lang=target_lang,
            units=fresh,
        )
        proj.mod_path = _norm(mod_path)
        proj.field_report = field_report
        proj.path = resolve_project_path(workdir, mod_path, target_lang)
        if proj.path.exists():
            old = cls.load(proj.path)
            proj._merge(old)
        return proj

    def _merge(self, old: "Project") -> None:
        by_key = {u.key: u for u in old.units}
        for u in self.units:
            prev = by_key.get(u.key)
            if prev is None:
                continue
            if prev.source == u.source:
                u.translation, u.status, u.note, u.lang = prev.translation, prev.status, prev.note, prev.lang
            elif prev.translation:
                u.status = ATTENTION
                u.note = f"O original mudou. Tradução antiga: {prev.translation}"
        self.source_lang = old.source_lang if self.source_lang == "auto" else self.source_lang

    # ------------------------------------------------------------ arquivo
    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("Projeto sem caminho para salvar.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with _SAVE_LOCK:  # a tradução (outra thread) e a janela podem salvar ao mesmo tempo
            payload = {
                "version": FORMAT_VERSION,
                "mod_name": self.mod_name,
                "mod_sha1": self.mod_sha1,
                "mod_path": self.mod_path,
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "units": [asdict(u) for u in self.units],
            }
            tmp = target.with_suffix(target.suffix + ".tmp")
            text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            tmp.write_text(text, encoding="utf-8")
            _replace_with_retry(tmp, target, text)  # troca atômica: nunca deixa o projeto pela metade
        self.path = target
        return target

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        proj = cls(
            mod_name=data["mod_name"],
            mod_sha1=data.get("mod_sha1", ""),
            mod_path=data.get("mod_path", ""),
            source_lang=data.get("source_lang", "auto"),
            target_lang=data.get("target_lang", "pt-BR"),
            units=[Unit(**u) for u in data["units"]],
        )
        proj.path = Path(path)
        return proj

    # ------------------------------------------------------------ consulta
    def stats(self) -> dict[str, int]:
        out = {s: 0 for s in STATUSES}
        for u in self.units:
            out[u.status] = out.get(u.status, 0) + 1
        out["total"] = len(self.units)
        return out

    def progress(self) -> float:
        """Fração (0 a 1) dos textos que têm decisão: traduzidos, revisados ou ignorados."""
        if not self.units:
            return 1.0
        done = sum(1 for u in self.units if u.status in (AUTO, REVIEWED, IGNORED))
        return done / len(self.units)

    def language_counts(self) -> dict[str, int]:
        """Quantos textos há por idioma detectado (só textos com letras, sem o nome dos records)."""
        counts: dict[str, int] = {}
        for u in self.units:
            if u.lang:
                counts[u.lang] = counts.get(u.lang, 0) + 1
        return counts

    def toolkit_units(self) -> list[TranslationUnit]:
        return [u.to_toolkit() for u in self.units]

    # ------------------------------------------------------------ edição
    def set_translation(self, key: tuple[str, str], text: str) -> Unit:
        """Edição manual: vira 'revisada' (ou 'pendente' se o texto ficou vazio)."""
        for u in self.units:
            if u.key == key:
                u.translation = text
                u.status = REVIEWED if text.strip() else PENDING
                u.note = ""
                return u
        raise KeyError(key)

    # ------------------------------------------------------------ PO
    def export_po(self) -> str:
        """Arquivo PO para editar no Poedit e similares."""
        return to_po(self.toolkit_units(), self.target_lang)

    def import_po(self, content: str) -> int:
        """Traz traduções de um PO. Devolve quantas foram aplicadas."""
        tk = self.toolkit_units()
        n = apply_po(tk, content)
        by_key = {t.key: t.translation for t in tk}
        for u in self.units:
            new = by_key.get(u.key, "")
            if new.strip() and new != u.translation:
                u.translation, u.status, u.note = new, REVIEWED, ""
        return n


def project_path(workdir: str | Path, mod_name: str, target_lang: str) -> Path:
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in mod_name)
    return Path(workdir) / f"{safe}.{target_lang}.ktproj.json"


def _norm(path: str | Path) -> str:
    """Forma única do caminho (maiúsculas/minúsculas e barras) para comparar donos de projeto."""
    p = os.path.abspath(str(path))
    return os.path.normcase(os.path.join(os.path.dirname(p), real_mod_name(os.path.basename(p))))


def _owner_of(file: Path) -> str:
    """Caminho do mod dono de um projeto salvo; '' se o projeto é antigo (sem dono) ou ilegível."""
    try:
        return str(json.loads(file.read_text(encoding="utf-8")).get("mod_path", ""))
    except (OSError, ValueError):
        return ""


def resolve_project_path(workdir: str | Path, mod_path: str | Path, target_lang: str) -> Path:
    """
    Arquivo de projeto de ESTE mod. Dois mods com o mesmo nome de arquivo (um no Workshop e
    outro na pasta do jogo) não dividem mais o progresso:
      1. já existe projeto com sufixo do caminho deste mod -> usa;
      2. o projeto "simples" (nome do arquivo) é deste mod, ou é antigo e sem dono -> usa;
      3. o projeto simples é de OUTRO mod -> usa o com sufixo (criado na primeira vez).
    Projetos antigos continuam valendo: o primeiro mod que os abrir passa a ser o dono.
    """
    me = _norm(mod_path)
    plain = project_path(workdir, real_mod_name(Path(mod_path).name), target_lang)
    suffixed = plain.with_name(
        plain.name.replace(".ktproj.json", f"~{hashlib.sha1(me.encode('utf-8')).hexdigest()[:8]}.ktproj.json"))
    if suffixed.exists():
        return suffixed
    if not plain.exists():
        return plain
    owner = _owner_of(plain)
    return plain if owner in ("", me) else suffixed


def load_mod(path: str | Path) -> ModFile:
    return load(Path(path).read_bytes())


def dump_mod(mod: ModFile) -> bytes:
    return dump(mod)
