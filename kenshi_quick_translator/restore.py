"""
Restaurar o mod original (desfazer a instalação do mod traduzido).

Só mexe em arquivos: não depende do toolkit. A instalação guarda o original como
"<nome>.mod.original" na pasta do mod; aqui ele volta ao lugar. A tradução que estava
instalada NÃO é apagada: fica ao lado como "<nome>.mod.traduzido", para poder voltar a ela.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .locate import ORIGINAL_SUFFIX

TRANSLATED_SUFFIX = ".traduzido"


@dataclass
class RestoreResult:
    mod_file: Path  # o .mod que voltou a ser o original
    kept_translation: Path | None  # onde ficou a tradução que estava instalada (None se não havia)


def installed_mod_path(kenshi_dir: str | Path, mod_name: str) -> Path:
    """Kenshi/mods/<nome>/<nome>.mod (mesma regra da instalação)."""
    stem = Path(mod_name).stem
    return Path(kenshi_dir) / "mods" / stem / (stem + ".mod")


def backup_path(kenshi_dir: str | Path, mod_name: str) -> Path:
    mod = installed_mod_path(kenshi_dir, mod_name)
    return mod.with_name(mod.name + ORIGINAL_SUFFIX)


def has_backup(kenshi_dir: str | Path, mod_name: str) -> bool:
    return backup_path(kenshi_dir, mod_name).is_file()


def restore_original(kenshi_dir: str | Path, mod_name: str) -> RestoreResult:
    """
    Põe o original de volta. Levanta FileNotFoundError se não há backup (nada foi instalado
    por este programa, ou o backup foi apagado). O backup é mantido (copiado, não movido):
    assim dá para traduzir de novo para outro idioma depois.
    """
    mod = installed_mod_path(kenshi_dir, mod_name)
    backup = mod.with_name(mod.name + ORIGINAL_SUFFIX)
    if not backup.is_file():
        raise FileNotFoundError(f"Não há cópia do original para restaurar ({backup.name}).")
    kept: Path | None = None
    if mod.is_file():
        if mod.read_bytes() == backup.read_bytes():
            kept = None  # já é o original: nada a guardar
        else:
            kept = mod.with_name(mod.name + TRANSLATED_SUFFIX)
            shutil.copy2(mod, kept)
    tmp = mod.with_name(mod.name + ".tmp-restaurar")
    shutil.copy2(backup, tmp)
    os.replace(tmp, mod)  # troca de uma vez: nunca fica um .mod pela metade
    return RestoreResult(mod_file=mod, kept_translation=kept)
