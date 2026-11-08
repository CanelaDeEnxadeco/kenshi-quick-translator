"""Captura de todos os temas (tela virtual):
    PYTHONPATH=. xvfb-run -a -s "-screen 0 1400x950x24" python tests/gui_themes.py pasta-de-capturas
"""
import subprocess, sys, tempfile, time, tkinter as tk
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from kenshi_quick_translator import gui  # noqa: E402
from kenshi_quick_translator.config import Config  # noqa: E402
from kenshi_quick_translator.session import Session  # noqa: E402


def pump(root, s=0.3):
    end = time.time() + s
    while time.time() < end:
        root.update(); time.sleep(0.01)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp()); data = work / "dados"; data.mkdir()
    cfg = Config(provider="simulado", target_lang="pt-BR", tour_done=True, theme="light")
    cfg.save = lambda path=None: None
    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=data)):
        app = gui.App(root)
    root.geometry("1300x760+0+0")
    pump(root, 1.0)
    for name in ("light", "dark", *gui.EFFECT_THEMES):
        app.apply_theme(name); pump(root, 0.9)
        subprocess.run(["import", "-window", "root", "-crop", "1300x760+0+0", str(out / f"t_{name}.png")], check=False)
    print("OK")
    root.destroy()


main()
