"""
Teste da janela de verdade, numa tela virtual:

    xvfb-run -a python tests/gui_smoke.py "caminho/do/mod.mod" [captura.png]

Monta uma pasta de Kenshi falsa com três mods (o que você passar, um misto
inglês+chinês e um só em inglês), usa o serviço simulado (sem internet) e uma
pasta de dados temporária. Nada fora da pasta temporária é gravado.
"""

import shutil
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

from test_core import make_mod  # noqa: E402

from kenshi_quick_translator import gui  # noqa: E402
from kenshi_quick_translator.config import Config  # noqa: E402
from kenshi_quick_translator.session import Session  # noqa: E402

MIXED = []
for i in range(14):
    MIXED.append(f"You talk too much and I am not your friend, stranger number {i}. /TEAMUP/ now.")
    MIXED.append(f"我不需要你的怜悯，别再烦我了，第{i}次。")
MIXED += ["Maybe.", "...", "你好"]

ENGLISH = [f"Nobody here has seen the caravan since the storm, friend number {i}." for i in range(10)]


def pump(root: tk.Tk, seconds: float = 0.3) -> None:
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.01)


def wait(root: tk.Tk, cond, what: str, timeout: float = 20) -> None:
    end = time.time() + timeout
    while time.time() < end:
        pump(root, 0.05)
        if cond():
            return
    raise AssertionError(f"tempo esgotado esperando: {what}")


def main() -> None:
    sample = Path(sys.argv[1])
    shot = sys.argv[2] if len(sys.argv) > 2 else None
    work = Path(tempfile.mkdtemp())

    # Kenshi falso
    kenshi = work / "Steam" / "steamapps" / "common" / "Kenshi"
    (kenshi / "data").mkdir(parents=True)
    (kenshi / "kenshi_x64.exe").write_bytes(b"")
    (kenshi / "data" / "mods.cfg").write_text("Mixed Dialogue.mod\nEnglish Only.mod\nrecruit Saelith.mod\n")
    for name, data in (("Mixed Dialogue", make_mod(MIXED, "Mixed Dialogue.mod")),
                       ("English Only", make_mod(ENGLISH, "English Only.mod")),
                       ("recruit Saelith", sample.read_bytes())):
        d = kenshi / "mods" / name
        d.mkdir(parents=True)
        (d / f"{name}.mod").write_bytes(data)

    cfg = Config(provider="simulado", kenshi_dir=str(kenshi), workers=4)
    cfg.save = lambda path=None: None  # não grava fora da pasta temporária

    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=work / "dados")):
        app = gui.App(root)
    pump(root)

    shown: list[tuple[str, str]] = []
    gui.messagebox.showinfo = lambda t, m, **k: shown.append((t, m))
    gui.messagebox.showwarning = lambda t, m, **k: shown.append((t, m))
    gui.messagebox.showerror = lambda t, m, **k: shown.append((t, m))
    gui.messagebox.askyesno = lambda *a, **k: True
    gui.filedialog.askdirectory = lambda **k: str(work / "saida")
    gui.open_with_system = lambda p: None

    # 1. lista de mods com idioma
    assert len(app.mod_tree.get_children()) == 3, app.entries
    wait(root, lambda: all(app.mod_tree.set(i, "idioma") != "…" for i in app.mod_tree.get_children()),
         "idioma de cada mod")
    labels = {app.mod_tree.item(i, "text"): app.mod_tree.set(i, "idioma") for i in app.mod_tree.get_children()}
    print("1. mods:", labels)
    assert "Chinês (zh)" in labels["Mixed Dialogue.mod"] and "Inglês (en)" in labels["Mixed Dialogue.mod"], labels
    assert labels["English Only.mod"] == "Inglês (en)", labels

    def select(name: str) -> None:
        iid = next(i for i in app.mod_tree.get_children() if app.mod_tree.item(i, "text") == name)
        app.mod_tree.selection_set(iid)

    # 2. abrir o mod misto: o programa sugere o modo de vários idiomas
    select("Mixed Dialogue.mod")
    wait(root, lambda: app.mod_var.get() == "Mixed Dialogue.mod" and not app._busy(), "abrir o mod misto")
    assert app.multi_var.get() is True
    assert app.src_checks["en"].get() and app.src_checks["zh"].get()
    assert not app.src_checks["ja"].get()
    print("2. mod misto aberto:", app.info_var.get())

    # 3. traduzir
    app.speed_scale.set(6)
    app.start_translate(False)
    wait(root, lambda: not app._busy(), "tradução do mod misto")
    pump(root, 0.3)
    st = app.session.project.stats()
    assert st["pendente"] == 0, st
    zh = [u for u in app.session.project.units if u.lang == "zh"]
    assert zh and all(u.translation.startswith("[PT]") for u in zh), "chinês não foi traduzido"
    assert all("/TEAMUP/" in u.translation for u in app.session.project.units if "/TEAMUP/" in u.source)
    print("3. traduzido:", st, "| chinês traduzido:", len(zh), "| ", app.status_var.get())

    # 4. editar uma linha e gerar o mod
    first = app.tree.get_children()[0]
    app.tree.selection_set(first)
    pump(root, 0.1)
    app.dst_text.delete("1.0", "end")
    app.dst_text.insert("1.0", "Texto revisado à mão. /TEAMUP/ agora.")
    app.validate_editor()
    print("4. editor:", app.check_var.get())
    app.apply_edit()
    pump(root, 0.2)
    assert app.session.project.units[int(first)].status == "revisada"
    app.build_mod()
    pump(root, 0.2)
    assert app.last_built and app.last_built.exists(), shown
    print("   gerado:", app.last_built.name)

    # os botões de baixo nunca podem ficar inalcançáveis, em tela grande ou de notebook
    pump(root, 0.5)
    root_bottom = root.winfo_rooty() + root.winfo_height()
    btn_bottom = app.btn_build.winfo_rooty() + app.btn_build.winfo_height()
    visible = app.btn_build.winfo_viewable() and btn_bottom <= root_bottom
    scrollable = app.scroller._bar_on
    print(f"   janela {root.winfo_width()}x{root.winfo_height()} | botão 'Gerar' visível: {visible} | rolagem disponível: {scrollable}")
    assert visible or scrollable, "o botão Gerar mod ficou cortado e sem rolagem"
    editor_h = app.dst_text.winfo_height()
    assert editor_h >= 30, f"editor espremido ({editor_h}px)"
    table_h = app.tree.winfo_height()
    assert table_h >= 120, f"tabela de revisão espremida ({table_h}px): menos de 5 linhas visíveis"
    print(f"   editor {editor_h}px | tabela de revisão {table_h}px")

    if shot:
        app.tree.selection_set(app.tree.get_children()[3])
        pump(root, 0.5)
        try:
            from PIL import ImageGrab

            ImageGrab.grab().save(shot)
            print("captura:", shot)
        except Exception as e:  # noqa: BLE001
            print("sem captura:", e)

    # 5. fila de vários mods, instalando no jogo ao terminar
    app.install_var.set(True)
    app.mod_tree.selection_set([i for i in app.mod_tree.get_children()
                                if app.mod_tree.item(i, "text") in ("English Only.mod", "recruit Saelith.mod")])
    pump(root, 0.5)
    assert "(2)" in app.btn_many.cget("text"), app.btn_many.cget("text")
    shown.clear()
    app.start_many()
    wait(root, lambda: not app._busy(), "fila de mods", timeout=30)
    pump(root, 0.3)
    out = work / "dados" / "mods_traduzidos"
    built = sorted(p.name for p in out.glob("*.mod"))
    print("5. fila:", built)
    assert "English Only PT-BR.mod" in built and "recruit Saelith PT-BR.mod" in built, built
    cfg_text = (kenshi / "data" / "mods.cfg").read_text()
    assert "English Only PT-BR.mod" in cfg_text and "recruit Saelith PT-BR.mod" in cfg_text, cfg_text
    assert (kenshi / "mods" / "English Only PT-BR" / "English Only PT-BR.mod").exists()
    assert cfg_text.index("English Only.mod") < cfg_text.index("English Only PT-BR.mod")  # depois do original
    print("   mods.cfg:", cfg_text.split())

    # 6. progresso aparece na lista depois da tradução
    wait(root, lambda: any(app.mod_tree.set(i, "prog") == "100%" for i in app.mod_tree.get_children()), "progresso 100%")
    print("6. progresso na lista:", {app.mod_tree.item(i, "text"): app.mod_tree.set(i, "prog") for i in app.mod_tree.get_children()})

    app.on_close()
    shutil.rmtree(work, ignore_errors=True)
    print("OK: janela funcionou do começo ao fim")


if __name__ == "__main__":
    main()
