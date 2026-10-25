"""
Configuração do usuário, em um JSON na pasta de dados do programa.

Guarda só escolhas (pastas, idioma, serviço). A chave de API é guardada em
texto simples nesse arquivo, com permissão restrita no Linux/macOS; quem
preferir pode deixá-la em uma variável de ambiente (KENSHI_TRADUTOR_KEY).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def app_dir() -> Path:
    """Pasta de dados do programa (config, memória de tradução, projetos)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    new = base / "KenshiQuickTranslator"
    _migrate_old_folder(base / OLD_FOLDER_NAME, new)
    return new


OLD_FOLDER_NAME = "KenshiTradutor"  # nome da pasta de dados até a 0.6.2 (o programa se chamava "Kenshi Tradutor")
_migrated = False


def _migrate_old_folder(old: Path, new: Path) -> None:
    """
    Primeira abertura depois da troca de nome: COPIA a pasta de dados antiga para a nova, para
    ninguém perder progresso, memória de tradução, glossário e configurações. A antiga não é
    apagada nem alterada. Só roda se a nova ainda não existe.
    """
    global _migrated
    if _migrated:
        return
    _migrated = True
    try:
        if old.is_dir() and not new.exists():
            import shutil

            shutil.copytree(old, new)
    except OSError:
        pass  # sem permissão ou disco cheio: o programa começa com pasta nova


@dataclass
class Config:
    kenshi_dir: str = ""
    workshop_dir: str = ""
    provider: str = "agregado"
    api_key: str = ""
    server_url: str = ""
    source_lang: str = "auto"
    target_lang: str = "pt-BR"
    keep_character_names: bool = True
    workers: int = 3  # lotes de tradução ao mesmo tempo
    multi_source: bool = False  # mod com mais de um idioma de origem
    source_langs: list[str] = field(default_factory=list)
    ptbr_fix: bool = False  # marca interna: já corrigiu o destino antigo 'pt' para pt-BR
    ui_lang: str = "pt"  # idioma da interface (pt, en, es)
    theme: str = "light"  # light, dark ou auto (segue o Windows)
    notify_switch: bool = True  # avisar quando trocar de serviço
    translation_mode: str = "completo"  # completo (mesmo nome, substitui o original) | dependente (arquivo pequeno "Nome IDIOMA.mod" que depende do original)
    copy_images: bool = True  # copiar imagem/ícone do mod original ao instalar
    translate_text_files: bool = True  # traduzir .txt de frases da pasta do mod (ex.: tips.txt) ao instalar
    translate_locale_files: bool = True  # juntar o .mo (idioma da interface) do mod ao idioma do jogo, traduzido, ao instalar
    safe_record_types: bool = True  # só traduzir campos extras de tipos de registro que o jogador vê (diálogos, itens...); evita corromper animações/arquivos
    tour_done: bool = False  # já mostrou o passo a passo da primeira abertura
    notify_done: bool = True  # som e piscar a janela quando a tradução/fila terminar
    font_scale: int = 100  # tamanho da letra em % (85 a 150)
    win_geometry: str = ""  # tamanho e posição da janela ao fechar (ex.: 1300x900+40+20)
    win_zoomed: bool = False  # fechou maximizada
    last_selection: list[str] = field(default_factory=list)  # caminhos dos mods que estavam selecionados
    mod_filter: str = "todos"  # filtro da lista de mods (ver gui.MODFILTER_LABEL)
    mod_sort: str = "padrao"  # ordem da lista de mods (ver gui.MODSORT_LABEL)
    services: list[dict] = field(default_factory=list)  # serviços com chave/IA do agregado (ver services.py)
    use_free: bool = True  # incluir os serviços gratuitos no agregado
    spread: bool = True  # dividir os lotes entre os serviços ao mesmo tempo
    free_order: list[str] = field(default_factory=lambda: ["google-free", "bing", "microsoft", "yandex", "google2"])  # ordem do agregado

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or app_dir() / "config.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        if not data.get("ptbr_fix"):  # versões antigas podiam ter ficado em "Português (Portugal)"
            known["target_lang"] = "pt-BR" if known.get("target_lang", "pt-BR") == "pt" else known.get("target_lang", "pt-BR")
            known["ptbr_fix"] = True
        cfg = cls(**known)
        cfg.api_key = os.environ.get("KENSHI_TRADUTOR_KEY", cfg.api_key)
        return cfg

    def save(self, path: Path | None = None) -> Path:
        path = path or app_dir() / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return path


def projects_dir() -> Path:
    return app_dir() / "projetos"


def memory_path() -> Path:
    return app_dir() / "memoria.sqlite"


def glossary_path() -> Path:
    return app_dir() / "glossario.json"
