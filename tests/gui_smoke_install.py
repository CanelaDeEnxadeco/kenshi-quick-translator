"""Instalar sem travar a janela e sem tocar na pasta do original (modo dependente):
    PYTHONPATH=. xvfb-run -a python tests/gui_smoke_install.py
"""
import sys, tempfile, time, tkinter as tk
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from kenshi_quick_translator import gui, i18n  # noqa: E402
from kenshi_quick_translator.config import Config  # noqa: E402
from kenshi_quick_translator.session import Session  # noqa: E402
from test_core import make_mod  # noqa: E402


def pump(root, s=0.3):
    end = time.time() + s
    while time.time() < end:
        root.update(); time.sleep(0.01)


work = Path(tempfile.mkdtemp()); data = work / "dados"; data.mkdir()
k = work / "K"; (k / "data").mkdir(parents=True); (k / "kenshi_x64.exe").write_bytes(b"")
orig = k / "mods" / "Foo"; (orig / "locale" / "en").mkdir(parents=True); (orig / "dll").mkdir()
(orig / "Foo.mod").write_bytes(make_mod(["Hello there, friend.", "Good day, traveler."]))
(orig / "RE_Kenshi.json").write_text("{}"); (orig / "dll" / "p.dll").write_bytes(b"MZ")
(orig / "locale" / "en" / "main.mo").write_bytes(b"")
cfg = Config(provider="simulado", kenshi_dir=str(k), target_lang="pt-BR", tour_done=True, translation_mode="dependente")
cfg.save = lambda path=None: None
root = tk.Tk()
with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=data)):
    app = gui.App(root)
pump(root, 0.8)
app.session.open_mod(orig / "Foo.mod")
from kenshi_quick_translator.core import translate_project
translate_project(app.session.project, app.session.make_provider(), glossary=app.session.glossary, memory=app.session.memory,
                  options=app.session.options(False))
app.session.project.save()
shown = []
with mock.patch.object(gui.messagebox, "askyesno", lambda *a, **k: True), \
     mock.patch.object(gui.messagebox, "showinfo", lambda *a, **k: shown.append(("info", a))), \
     mock.patch.object(gui.messagebox, "showerror", lambda *a, **k: shown.append(("erro", a))):
    t0 = time.time(); ticks = 0
    app.install_mod()
    while not shown and time.time() - t0 < 20:
        root.update(); ticks += 1; time.sleep(0.01)
assert shown and shown[0][0] == "info", shown
assert ticks > 3, "janela ficou parada"
assert not (k / "mods" / "Foo" / "locale_off").exists(), "mexeu na pasta do original"
assert (orig / "RE_Kenshi.json").is_file()
dep = [p for p in (k / "mods").iterdir() if p.name != "Foo"]
print([p.name for p in dep], [f.name for p in dep for f in p.iterdir()])
assert dep and not any((p / "RE_Kenshi.json").exists() or (p / "dll").exists() for p in dep)
print("OK")
root.destroy()
