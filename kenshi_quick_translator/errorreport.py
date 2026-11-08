"""Relatório de erro para o usuário copiar e colar (sem chaves de API, sem caminhos pessoais além do nome do mod)."""
from __future__ import annotations

import datetime
import faulthandler
import platform
import sys
import threading
import traceback
from pathlib import Path

MAX_LOG = 300_000  # bytes; acima disso o arquivo recomeça (o antigo vira .antigo)
_fault_file = None


def build_report(version: str, info: dict, last_error: str = "") -> str:
    lines = [f"Kenshi Quick Translator {version}",
             f"Python {sys.version.split()[0]} | {platform.platform()}"]
    for k, v in info.items():
        if v not in (None, ""):
            lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("Último erro:" if last_error else "Nenhum erro registrado nesta sessão.")
    if last_error:
        lines.append(last_error.rstrip())
    return "\n".join(lines)


def format_exc(exc_type, exc, tb) -> str:
    return "".join(traceback.format_exception(exc_type, exc, tb))


def log_path() -> Path:
    from .config import app_dir
    return app_dir() / "erros.log"


def log_error(text: str, path: Path | None = None) -> None:
    """Acrescenta um erro ao arquivo erros.log (nunca levanta erro, não grava chaves nem textos do mod)."""
    try:
        path = path or log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > MAX_LOG:
            path.replace(path.with_suffix(".antigo"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n{text.rstrip()}\n")
    except Exception:  # noqa: BLE001
        pass


def install_crash_log(path: Path | None = None) -> None:
    """Erros em segundo plano e quedas do próprio Python (que fecham o programa sem aviso) também vão para o arquivo."""
    global _fault_file
    try:
        path = path or log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _fault_file = open(path, "a", encoding="utf-8")  # fica aberto de propósito: o faulthandler escreve nele
        _fault_file.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} (programa aberto) ===\n")
        _fault_file.flush()
        faulthandler.enable(file=_fault_file, all_threads=True)
    except Exception:  # noqa: BLE001
        pass

    def thread_hook(args) -> None:
        log_error("Erro em segundo plano:\n" + format_exc(args.exc_type, args.exc_value, args.exc_traceback), path)

    threading.excepthook = thread_hook
