"""Janela de verdade (tela virtual) para a 0.6.6: as duas opções novas nas configurações.
    xvfb-run -a python tests/gui_smoke66.py [pasta-de-capturas]
"""
import subprocess, sys, tempfile, time, tkinter as tk
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from kenshi_quick_translator import gui, i18n, mofile  # noqa: E402
from kenshi_quick_translator.config import Config  # noqa: E402
from kenshi_quick_translator.session import Session  # noqa: E402
from test_core import make_mod  # noqa: E402


def pump(root, s=0.3):
    end = time.time() + s
    while time.time() < end:
        root.update(); time.sleep(0.01)


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def mo(entries, header="Content-Type: text/plain; charset=UTF-8\n"):
    return mofile.write_mo(mofile.Catalog(entries=entries, header=header))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else None
    work = Path(tempfile.mkdtemp())
    data = work / "dados"; data.mkdir()
    kenshi = work / "K"; (kenshi / "data" / "locale" / "pt_BR").mkdir(parents=True); (kenshi / "mods" / "Foo" / "locale" / "en").mkdir(parents=True)
    (kenshi / "kenshi_x64.exe").write_bytes(b"")
    (kenshi / "data" / "locale" / "pt_BR" / "main.mo").write_bytes(
        mo({"New Game": "Novo jogo"}, "Content-Type: text/plain; charset=UTF-8\nLanguage: pt_BR\n"))
    foo = kenshi / "mods" / "Foo"
    (foo / "Foo.mod").write_bytes(make_mod(["Hello there, friend.", "Good day, traveler."]))
    (foo / "tips.txt").write_text("Too many corpses left lying around will attract predators.\n" * 4)
    (foo / "namesF.txt").write_text("Vivimade Poojar\nBriana Aylwate\nAmamika Wincbick\n")
    (foo / "locale" / "en" / "main.mo").write_bytes(mo({"Katanas": "Lightsabers"}))
    cfg = Config(provider="simulado", kenshi_dir=str(kenshi), target_lang="pt-BR", tour_done=True)
    cfg.save = lambda path=None: None
    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=data)):
        app = gui.App(root)
    pump(root, 1)
    errors = []
    with mock.patch.object(gui.messagebox, "showinfo", lambda *a, **k: errors.append(("info", a))), \
         mock.patch.object(gui.messagebox, "showerror", lambda *a, **k: errors.append(("erro", a))):
        i18n.set_language("pt")
        app.open_settings()
        pump(root, 0.4)
        top = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        checks = [str(w.cget("text")) for w in walk(top) if isinstance(w, gui.ttk.Checkbutton)]
        print([c for c in checks if "mod" in c.lower()])
        assert any("pasta locale" in c for c in checks) and any("dicas de carregamento" in c for c in checks)
        if out:
            subprocess.run(["import", "-window", "root", str(Path(out) / "config_pt.png")], check=False)
    assert not [e for e in errors if e[0] == "erro"], errors
    print("OK")
    root.destroy()


main()
