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
        )

    @classmethod
    def default(cls) -> "Glossary":
        text = resources.files("kenshi_quick_translator").joinpath("default_glossary.json").read_text(encoding="utf-8")
        data = json.loads(text)
        return cls(terms=dict(data.get("terms", {})), case_sensitive=bool(data.get("case_sensitive", True)))

    def save(self, path: str | Path) -> None:
        payload = {"case_sensitive": self.case_sensitive, "terms": self.terms}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
