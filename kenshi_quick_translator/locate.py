"""
Acha o Kenshi e a pasta do Workshop, e lista os mods instalados.

Em vez de depender de o programa estar numa pasta específica, procura nos
lugares comuns (Steam em qualquer biblioteca, GOG, Linux/Steam Deck) e
aceita um caminho escolhido pelo usuário. Cada mod é identificado pelo
CAMINHO, então dois mods com o mesmo nome de arquivo não se sobrescrevem.
"""

from __future__ import annotations

import os
import re
import string
import sys
from dataclasses import dataclass
from pathlib import Path

ORIGINAL_SUFFIX = ".original"  # backup do .mod original na pasta do jogo: "Nome.mod.original"


def real_mod_name(name: str) -> str:
    """Nome do mod de verdade: 'Nome.mod.original' (backup) vira 'Nome.mod'."""
    return name[: -len(ORIGINAL_SUFFIX)] if name.lower().endswith(".mod" + ORIGINAL_SUFFIX) else name


KENSHI_APP_ID = "233860"
GAME_EXES = ("kenshi_x64.exe", "kenshi_gog_x64.exe", "kenshi.exe")


@dataclass
class KenshiDirs:
    kenshi: Path | None = None
    workshop: Path | None = None
    how: str = ""  # como foi encontrado, para mostrar ao usuário


@dataclass
class ModEntry:
    name: str  # nome do arquivo, ex.: "Kaizo.mod"
    path: Path
    source: str  # 'local' ou 'workshop'
    size: int


def is_kenshi_dir(p: Path) -> bool:
    if not p.is_dir():
        return False
    names = {c.name.lower() for c in p.iterdir()} if os.access(p, os.R_OK) else set()
    return "data" in names and (any(e in names for e in GAME_EXES) or "mods" in names)


def _steam_libraries(steam_root: Path) -> list[Path]:
    """Bibliotecas do Steam, lendo libraryfolders.vdf."""
    libs = [steam_root]
    vdf = steam_root / "steamapps" / "libraryfolders.vdf"
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libs
    for m in re.finditer(r'"path"\s+"([^"]+)"', text):
        p = Path(m.group(1).replace("\\\\", "\\"))
        if p not in libs:
            libs.append(p)
    return libs


def _candidate_steam_roots() -> list[Path]:
    roots: list[Path] = []
    if sys.platform == "win32":
        drives = [f"{d}:\\" for d in string.ascii_uppercase if Path(f"{d}:\\").exists()]
        for pf in ("Program Files (x86)", "Program Files"):
            for d in drives:
                roots.append(Path(d) / pf / "Steam")
        for d in drives:
            roots += [Path(d) / "Steam", Path(d) / "SteamLibrary"]
    else:
        home = Path.home()
        roots += [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam",
            home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        ]
    return roots


def find_kenshi(manual_kenshi: str = "", manual_workshop: str = "") -> KenshiDirs:
    """Procura o Kenshi. Caminhos manuais têm prioridade sobre a busca."""
    result = KenshiDirs()

    if manual_kenshi and is_kenshi_dir(Path(manual_kenshi)):
        result.kenshi, result.how = Path(manual_kenshi), "escolhido por você"
    env = os.environ.get("KENSHI_DIR")
    if result.kenshi is None and env and is_kenshi_dir(Path(env)):
        result.kenshi, result.how = Path(env), "variável KENSHI_DIR"

    if result.kenshi is None:
        for root in _candidate_steam_roots():
            for lib in _steam_libraries(root):
                game = lib / "steamapps" / "common" / "Kenshi"
                if is_kenshi_dir(game):
                    result.kenshi, result.how = game, "Steam"
                    break
            if result.kenshi:
                break

    if result.kenshi is None and sys.platform == "win32":
        for d in (f"{c}:\\" for c in string.ascii_uppercase):
            for rel in ("GOG Games/Kenshi", "Program Files (x86)/GOG Galaxy/Games/Kenshi", "GOG Galaxy/Games/Kenshi"):
                game = Path(d) / rel
                if is_kenshi_dir(game):
                    result.kenshi, result.how = game, "GOG"
                    break
            if result.kenshi:
                break

    # Workshop: fica na mesma biblioteca do jogo (…/steamapps/workshop/content/233860).
    if manual_workshop and Path(manual_workshop).is_dir():
        result.workshop = Path(manual_workshop)
    elif result.kenshi is not None:
        steamapps = result.kenshi.parent.parent  # …/steamapps/common/Kenshi -> …/steamapps
        ws = steamapps / "workshop" / "content" / KENSHI_APP_ID
        if ws.is_dir():
            result.workshop = ws
    return result


def scan_mods(dirs: KenshiDirs) -> list[ModEntry]:
    """Lista os .mod instalados (local e Workshop), cada um por caminho."""
    found: list[ModEntry] = []
    if dirs.kenshi is not None:
        mods = dirs.kenshi / "mods"
        if mods.is_dir():
            for sub in sorted(p for p in mods.iterdir() if p.is_dir()):
                for f in sorted(sub.glob("*.mod")):
                    # se o Kenshi Quick Translator já trocou este .mod por uma tradução, o original está no backup
                    backup = f.with_name(f.name + ORIGINAL_SUFFIX)
                    src = backup if backup.is_file() else f
                    found.append(ModEntry(f.name, src, "local", src.stat().st_size))
    if dirs.workshop is not None and dirs.workshop.is_dir():
        for sub in sorted(p for p in dirs.workshop.iterdir() if p.is_dir()):
            for f in sorted(sub.glob("*.mod")):
                found.append(ModEntry(f.name, f, "workshop", f.stat().st_size))
    return found
