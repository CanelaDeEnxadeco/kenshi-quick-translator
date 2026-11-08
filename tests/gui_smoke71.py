"""0.7.1-ish: temas Preto eclipse / Branco lunar + configurações com dicas ao parar o mouse:
    PYTHONPATH=. xvfb-run -a -s "-screen 0 1400x950x24" python tests/gui_smoke71.py [pasta-de-capturas]
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


def shot(out, name):
    if out:
        subprocess.run(["import", "-window", "root", str(Path(out) / name)], check=False)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else None
    work = Path(tempfile.mkdtemp()); data = work / "dados"; data.mkdir()
    cfg = Config(provider="simulado", target_lang="pt-BR", tour_done=True, theme="preto")
    cfg.save = lambda path=None: None
    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=data)):
        app = gui.App(root)
    root.geometry("1300x760+0+0")
    pump(root, 1.0)
    for name in ("preto", "branco"):
        app.apply_theme(name); pump(root, 0.8)
        assert app.galaxy is not None and app._fx_theme == name
        shot(out, f"tema_{name}.png")
    app.apply_theme("branco"); pump(root, 0.3)
    app.open_settings(); pump(root, 0.6)
    win = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    win.geometry("+300+20"); pump(root, 0.5)
    shot(out, "cfg_branco.png")
    # dica ao parar o mouse
    def find(w, txt):
        for c in w.winfo_children():
            try:
                if txt in str(c.cget("text")):
                    return c
            except tk.TclError:
                pass
            r = find(c, txt)
            if r:
                return r
    cb = find(win, "tips.txt e names")
    assert cb is not None
    cb.event_generate("<Enter>"); pump(root, 0.2)
    tops = [w for w in win.winfo_children() if isinstance(w, tk.Toplevel)]
    assert not tops, "a dica apareceu antes de o mouse parar"
    pump(root, 0.8)
    tops = [w for w in cb.winfo_children() if isinstance(w, tk.Toplevel)]
    assert tops, "a dica nao apareceu depois de parar"
    shot(out, "cfg_dica.png")
    cb.event_generate("<Leave>"); pump(root, 0.2)
    assert not [w for w in cb.winfo_children() if isinstance(w, tk.Toplevel)]
    app.apply_theme("preto"); pump(root, 0.5)
    shot(out, "cfg_preto.png")
    print("OK")
    root.destroy()


main()
