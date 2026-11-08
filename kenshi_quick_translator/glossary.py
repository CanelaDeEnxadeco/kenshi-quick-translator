"""
Glossário: termos que devem sair sempre do mesmo jeito.

Arquivo JSON simples:

    {
      "case_sensitive": true,
      "terms": {
        "Holy Nation": "Nação Sagrada",
        "Hub": null
      }
    }

Valor texto = esse é o termo traduzido. Valor null (ou vazio) = manter como
está, sem traduzir (bom para nomes próprios).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path


@dataclass
class Glossary:
    terms: dict[str, str | None] = field(default_factory=dict)
    case_sensitive: bool = True
    lang: str | None = None  # idioma de destino a que os termos pertencem (ex.: "es")

    def __post_init__(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        keys = sorted((k for k in self.terms if k.strip()), key=len, reverse=True)
        self._lookup = {(k if self.case_sensitive else k.casefold()): k for k in keys}
        if not keys:
            self._re = None
            return
        alt = "|".join(re.escape(k) for k in keys)
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._re = re.compile(rf"(?<!\w)(?:{alt})(?!\w)", flags)

    def set(self, term: str, translation: str | None) -> None:
        self.terms[term] = translation or None
        self._rebuild()

    def remove(self, term: str) -> None:
        self.terms.pop(term, None)
        self._rebuild()

    def find(self, text: str) -> list[tuple[int, int, str]]:
        """Ocorrências como (início, fim, texto final que deve aparecer)."""
        if self._re is None:
            return []
        out: list[tuple[int, int, str]] = []
        for m in self._re.finditer(text):
            found = m.group(0)
            key = self._lookup.get(found if self.case_sensitive else found.casefold())
            target = self.terms.get(key) if key is not None else None
            out.append((m.start(), m.end(), target if target else found))
        return out

    # ---- arquivo ----
    @classmethod
    def load(cls, path: str | Path) -> "Glossary":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            terms=dict(data.get("terms", {})),
            case_sensitive=bool(data.get("case_sensitive", True)),
            lang=data.get("idioma") or None,
        )

    @classmethod
    def default(cls) -> "Glossary":
        text = resources.files("kenshi_quick_translator").joinpath("default_glossary.json").read_text(encoding="utf-8")
        data = json.loads(text)
        return cls(terms=dict(data.get("terms", {})), case_sensitive=bool(data.get("case_sensitive", True)),
                   lang=data.get("idioma") or "pt-BR")

    def merge(self, terms: dict[str, str | None], overwrite: bool = False) -> tuple[int, int, int]:
        """Junta termos (de um preset, por exemplo). Devolve (novos, atualizados, ignorados).

        Sem `overwrite`, um termo que você já tem fica como está (suas edições nunca são apagadas).
        """
        added = updated = skipped = 0
        for term, tr in terms.items():
            if not term.strip():
                continue
            if term not in self.terms:
                self.terms[term] = tr or None
                added += 1
            elif (self.terms[term] or None) == (tr or None):
                skipped += 1
            elif overwrite:
                self.terms[term] = tr or None
                updated += 1
            else:
                skipped += 1
        self._rebuild()
        return added, updated, skipped

    def save(self, path: str | Path) -> None:
        payload: dict = {"case_sensitive": self.case_sensitive}
        if self.lang:
            payload["idioma"] = self.lang
        payload["terms"] = self.terms
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---- presets prontos (nomes oficiais do Kenshi) ----
def list_presets() -> list[dict]:
    """Presets que acompanham o programa: [{id, nome, descricao, idioma, total}], em ordem."""
    out: list[dict] = []
    folder = resources.files("kenshi_quick_translator").joinpath("presets")
    try:
        files = sorted((f for f in folder.iterdir() if f.name.endswith(".json")), key=lambda f: f.name)
    except (FileNotFoundError, OSError):
        return out
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({
            "id": f.name[:-5],
            "nome": data.get("nome", f.name[:-5]),
            "descricao": data.get("descricao", ""),
            "idioma": data.get("idioma", ""),
            "total": len(data.get("terms", {})),
        })
    return out


def presets_for(target_lang: str) -> tuple[list[dict], bool]:
    """
    Presets do idioma de destino. Devolve (lista, oficial). `oficial` = vêm da tradução oficial do Kenshi nesse idioma.
    Sem tradução oficial (italiano, ucraniano, polonês, turco, português de Portugal...), devolve só o preset
    neutro "manter nomes originais" (idioma "*"), que é uma escolha, não a regra de uma tradução oficial.
    """
    allp = list_presets()
    official = [p for p in allp if p["idioma"] == target_lang]
    if official:
        return official, True
    return [p for p in allp if p["idioma"] == "*"], False


def default_preset_ids(target_lang: str) -> list[str]:
    """Presets que valem como ponto de partida: só nomes próprios (cidades, facções, personagens com nome).
    Sem tradução oficial no idioma, é o preset neutro "manter nomes originais"."""
    presets, official = presets_for(target_lang)
    if not official:
        return [p["id"] for p in presets]
    wanted = ("_cidades", "_faccoes", "_personagens")
    return [p["id"] for p in presets if p["id"].endswith(wanted)]


def load_preset(preset_id: str) -> dict[str, str | None]:
    """Termos de um preset (valor None = manter como está, sem traduzir)."""
    if not re.fullmatch(r"[\w.-]+", preset_id):
        raise ValueError(f"Preset inválido: {preset_id!r}")
    text = resources.files("kenshi_quick_translator").joinpath("presets", preset_id + ".json").read_text(encoding="utf-8")
    return dict(json.loads(text).get("terms", {}))
