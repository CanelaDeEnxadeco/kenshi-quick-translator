"""Janela de verdade (tela virtual) para a 0.6.1: Configurações > Limpar dados.
    xvfb-run -a python tests/gui_smoke61.py [pasta-de-capturas]
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


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else None
    work = Path(tempfile.mkdtemp())
    data = work / "dados"
    (data / "projetos" / "backup").mkdir(parents=True)
    (data / "projetos" / "A.pt-BR.ktproj.json").write_text("{}")
    (data / "projetos" / "backup" / "A.bak").write_text("x")
    (data / "idiomas.json").write_text("{}")
    kenshi = work / "K"; (kenshi / "data").mkdir(parents=True); (kenshi / "mods").mkdir()
    (kenshi / "kenshi_x64.exe").write_bytes(b"")
    (kenshi / "mods" / "keep.mod.original").write_bytes(b"orig")
    cfg = Config(provider="simulado", kenshi_dir=str(kenshi))
    cfg.save = lambda path=None: None
    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=data)):
        app = gui.App(root)
    pump(root, 1)
    asked = []
    infos = []
    with mock.patch.object(gui.messagebox, "askyesno", lambda *a, **k: asked.append(a) or True), \
         mock.patch.object(gui.messagebox, "showinfo", lambda *a, **k: infos.append(a)):
        for lang in ("pt", "en", "ru", "zh"):
            i18n.set_language(lang)
            app.open_cleanup()
            pump(root, 0.4)
            top = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            texts = [str(w.cget("text")) for w in walk(top) if isinstance(w, (tk.Label, gui.ttk.Checkbutton, gui.ttk.Button))]
            print(lang, "|", texts[1], "|", texts[-2:])
            if lang == "en":
                shot = out and subprocess.run(["import", "-window", "root", str(Path(out) / "limpar_en.png")], check=False)
            top.destroy()
        i18n.set_language("pt")
        app.open_cleanup()
        pump(root, 0.4)
        top = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        if out:
            subprocess.run(["import", "-window", "root", str(Path(out) / "limpar_pt.png")], check=False)
        apagar = [w for w in walk(top) if isinstance(w, gui.ttk.Button) and w.cget("text") in ("Apagar", "Delete")][0]
        apagar.invoke()
        pump(root, 0.4)
    assert asked, "deveria pedir confirmação"
    assert not list((data / "projetos").glob("*.json")), "projetos deveriam ter sido apagados"
    assert not (data / "projetos" / "backup").exists()
    assert not (data / "idiomas.json").exists()
    assert (kenshi / "mods" / "keep.mod.original").exists(), "NUNCA mexer na pasta do Kenshi"
    print("avisos:", infos)
    print("OK")
    root.destroy()


main()
