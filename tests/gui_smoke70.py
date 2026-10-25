"""Tema Azul galáxia em janela de verdade (tela virtual):
    PYTHONPATH=. xvfb-run -a python tests/gui_smoke70.py [pasta-de-capturas]
"""
import subprocess, sys, tempfile, time, tkinter as tk
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from kenshi_quick_translator import gui, i18n  # noqa: E402
from kenshi_quick_translator.config import Config  # noqa: E402
from kenshi_quick_translator.session import Session  # noqa: E402


def pump(root, s=0.3):
    end = time.time() + s
    while time.time() < end:
        root.update(); time.sleep(0.01)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else None
    work = Path(tempfile.mkdtemp()); data = work / "dados"; data.mkdir()
    cfg = Config(provider="simulado", target_lang="pt-BR", tour_done=True, theme="galaxia")
    cfg.save = lambda path=None: None
    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=data)):
        app = gui.App(root)
    pump(root, 1.0)
    assert app.galaxy is not None and len(app.galaxy._flies) >= 18
    pos1 = [(f["x"], f["y"]) for f in app.galaxy._flies[:5]]
    pump(root, 0.6)
    pos2 = [(f["x"], f["y"]) for f in app.galaxy._flies[:5]]
    assert pos1 != pos2, "vagalumes não se mexem"
    if out:
        subprocess.run(["import", "-window", "root", str(Path(out) / "galaxia_1.png")], check=False)
    app.apply_theme("dark"); pump(root, 0.3)
    assert app.galaxy is None and app.hdr_title.winfo_manager() == "pack"
    app.apply_theme("galaxia"); pump(root, 0.5)
    assert app.galaxy is not None
    app.open_settings(); pump(root, 0.4)
    if out:
        subprocess.run(["import", "-window", "root", str(Path(out) / "galaxia_cfg.png")], check=False)
    if out:
        for name in ("verde", "vermelho", "amarelo", "laranja", "roxo", "rosa"):
            app.apply_theme(name); pump(root, 0.5)
            assert app.galaxy is not None and app._fx_theme == name
            subprocess.run(["import", "-window", "root", str(Path(out) / f"tema_{name}.png")], check=False)
    print("OK")
    root.destroy()


main()
