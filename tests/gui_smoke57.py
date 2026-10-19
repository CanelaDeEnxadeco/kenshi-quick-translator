"""
Janela de verdade (tela virtual) para a 0.5.7: passo a passo, dicas, ícones dos mods e gráfico de velocidade.

    xvfb-run -a python tests/gui_smoke57.py "caminho/do/mod.mod" [pasta-de-capturas]
"""
import subprocess
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


def pump(root, seconds=0.3):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.01)


def shot(folder, name):
    if folder:
        subprocess.run(["import", "-window", "root", str(Path(folder) / name)], check=False)


def main():
    sample = Path(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    work = Path(tempfile.mkdtemp())
    kenshi = work / "Steam" / "steamapps" / "common" / "Kenshi"
    (kenshi / "data").mkdir(parents=True)
    (kenshi / "kenshi_x64.exe").write_bytes(b"")
    (kenshi / "data" / "mods.cfg").write_text("")
    from PIL import Image

    for n, name in enumerate(("Mixed Dialogue", "English Only", "recruit Saelith")):
        d = kenshi / "mods" / name
        d.mkdir(parents=True)
        data = sample.read_bytes() if n == 2 else make_mod([f"Nobody has seen caravan number {i}." for i in range(8)], f"{name}.mod")
        (d / f"{name}.mod").write_bytes(data)
        if n == 0:
            Image.new("RGB", (512, 512), (200, 40, 40)).save(d / f"{name}.png")
        if n == 1:
            Image.new("RGB", (800, 400), (40, 90, 200)).save(d / "preview.jpg")  # JPG: só com Pillow
    cfg = Config(provider="simulado", kenshi_dir=str(kenshi), workers=4)
    cfg.save = lambda path=None: None
    root = tk.Tk()
    with mock.patch.object(gui, "Session", lambda: Session(cfg, workdir=work / "dados")):
        app = gui.App(root)
    pump(root, 1.5)

    # --- dicas
    assert app.src_box is not None
    tips = sum(1 for w in gui.App._attach_tips.__code__.co_consts if isinstance(w, str))
    print("dicas: método ok" if tips else "")

    # --- ícones dos mods
    deadline = time.time() + 10
    while time.time() < deadline and any(not app.mod_tree.item(i, "image") for i in app.mod_tree.get_children()
                                         if "recruit" not in app.mod_tree.item(i, "text")):
        pump(root, 0.1)
    with_icon = {app.mod_tree.item(i, "text"): bool(app.mod_tree.item(i, "image")) for i in app.mod_tree.get_children()}
    print("ícones:", with_icon)
    assert with_icon["Mixed Dialogue.mod"] and with_icon["English Only.mod"], with_icon
    assert not with_icon["recruit Saelith.mod"], "mod sem imagem não deve ter ícone"

    # --- gráfico de velocidade (eventos de progresso falsos, 20 textos por segundo)
    app.rate.reset()
    for k in range(40):
        app.events.put(("progress", k * 5, 300, "Traduzindo"))
        pump(root, 0.25)
    print("pontos do gráfico:", len(app.rate.points), "| atual:", round(app.rate.current), "| pico:", round(app.rate.peak))
    assert len(app.rate.points) >= 3 and 900 < app.rate.current < 1500, app.rate.points
    assert app.spark.find_all(), "o gráfico não desenhou nada"
    shot(out, "1_principal.png")

    # --- passo a passo
    app.open_tour(first_run=True)
    pump(root, 0.5)
    assert app.tour is not None and len(app.tour.steps) == 4, app.tour and app.tour.steps
    for step in range(4):
        t = app.tour
        key = t.steps[step][0]
        print(f"passo {step + 1}:", t.title.cget("text"), "| próximo:", t.b_next.cget("text"))
        if key in ("mods", "how", "review"):
            assert t.saved is not None and int(float(t.saved[0].cget("highlightthickness"))) == 4, "cartão não foi realçado"
        shot(out, f"2_passo{step + 1}.png")
        assert t.win.winfo_exists()
        t.next()
        pump(root, 0.3)
    assert app.tour is None
    assert cfg.tour_done is True
    for c in app.cards.values():  # tudo voltou ao normal
        assert int(float(c.cget("highlightthickness"))) == 1
    print("passo a passo concluído; realces desfeitos; tour_done =", cfg.tour_done)

    # --- idioma chinês: tour e dicas sem erro
    gui.i18n.set_language("zh")
    app.open_tour(first_run=False)
    pump(root, 0.5)
    print("tour em chinês:", app.tour.title.cget("text"), "|", app.tour.count.cget("text"))
    shot(out, "3_tour_zh.png")
    app.tour.close()
    gui.i18n.set_language("pt")
    print("OK")
    root.destroy()


if __name__ == "__main__":
    main()
