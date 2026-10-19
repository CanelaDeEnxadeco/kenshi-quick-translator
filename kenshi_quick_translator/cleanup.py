"""
Limpeza dos dados do PROGRAMA (a pasta de dados dele). Lógica pura, sem janela.

Só apaga arquivos conhecidos dentro da pasta de dados. NUNCA mexe na pasta do Kenshi:
os mods, o mods.cfg e as cópias ".original" ficam como estão (são elas que permitem
"Restaurar o original").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJ_SUFFIX = ".ktproj.json"

# chave, rótulo, explicação
CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("projetos", "Traduções salvas (progresso de cada mod)",
     "Todos os mods voltam a 0%. Os mods em si não são alterados."),
    ("backup", "Cópias de segurança dos projetos",
     "A pasta 'backup' criada ao zerar ou refazer traduções."),
    ("memoria", "Memória de tradução",
     "Frases já traduzidas que o programa reaproveita. Apagar só deixa as próximas traduções mais lentas."),
    ("idiomas", "Idiomas detectados nos mods",
     "Cache da detecção de idioma. É refeito sozinho."),
    ("glossario", "Glossário",
     "Os termos que você cadastrou."),
    ("config", "Configurações e chaves dos serviços",
     "Volta tudo ao padrão: idioma, tema, pasta do Kenshi e as chaves de DeepL, IAs etc. serão apagadas."),
)
DEFAULT_ON = ("projetos", "backup", "memoria", "idiomas")  # glossário e configurações: só se a pessoa marcar


@dataclass
class Item:
    key: str
    label: str
    note: str
    files: int
    size: int  # bytes


def _paths(folder: Path, key: str) -> list[Path]:
    """Arquivos de uma categoria (só os conhecidos, dentro da pasta de dados)."""
    folder = Path(folder)
    if key == "projetos":
        pdir = folder / "projetos"
        return sorted(p for p in pdir.glob(f"*{PROJ_SUFFIX}") if p.is_file()) if pdir.is_dir() else []
    if key == "backup":
        bdir = folder / "projetos" / "backup"
        return sorted(p for p in bdir.iterdir() if p.is_file()) if bdir.is_dir() else []
    if key == "memoria":
        return [p for n in ("memoria.sqlite", "memoria.sqlite-wal", "memoria.sqlite-shm", "memoria.sqlite-journal")
                if (p := folder / n).is_file()]
    if key == "idiomas":
        return [p for n in ("idiomas.json", "idiomas.tmp") if (p := folder / n).is_file()]
    if key == "glossario":
        p = folder / "glossario.json"
        return [p] if p.is_file() else []
    if key == "config":
        p = folder / "config.json"
        return [p] if p.is_file() else []
    raise KeyError(key)


def scan(folder: str | Path) -> list[Item]:
    items = []
    for key, label, note in CATEGORIES:
        files = _paths(Path(folder), key)
        size = 0
        for f in files:
            try:
                size += f.stat().st_size
            except OSError:
                pass
        items.append(Item(key, label, note, len(files), size))
    return items


def human_size(n: int) -> str:
    v = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if v < 1024 or unit == "GB":
            return f"{int(v)} {unit}" if unit == "B" else f"{v:.1f} {unit}"
        v /= 1024
    return f"{n} B"


@dataclass
class CleanResult:
    removed: dict[str, int]
    failed: list[str]

    @property
    def total(self) -> int:
        return sum(self.removed.values())


def clean(folder: str | Path, keys, *, before=None) -> CleanResult:
    """
    Apaga as categorias pedidas. `before(key)` é chamado antes de cada categoria (a janela usa
    para fechar a memória de tradução, que fica aberta). Erros de arquivo não param o resto.
    """
    valid = {k for k, _, _ in CATEGORIES}
    removed: dict[str, int] = {}
    failed: list[str] = []
    for key in [k for k, _, _ in CATEGORIES if k in set(keys) & valid]:
        if before:
            try:
                before(key)
            except Exception as e:  # noqa: BLE001 - não impede a limpeza
                failed.append(f"{key}: {e}")
        n = 0
        for f in _paths(Path(folder), key):
            try:
                f.unlink()
                n += 1
            except OSError as e:
                failed.append(f"{f.name}: {e}")
        removed[key] = n
    if "backup" in keys:  # remove a pasta 'backup' se ficou vazia
        try:
            (Path(folder) / "projetos" / "backup").rmdir()
        except OSError:
            pass
    return CleanResult(removed, failed)
