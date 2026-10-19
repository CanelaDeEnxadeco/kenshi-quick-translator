"""
Medição com um mod GRANDE (sintético), para ver onde o tempo vai e se algo
fica lento demais com dezenas de milhares de textos.

    python tests/bench_large.py --texts 50000 --delay 0 --workers 6
    python tests/bench_large.py --texts 20000 --delay 0.05 --workers 1,3,6

--delay é o tempo, em segundos, que cada pedido ao "serviço" demora (simulado).
Serviços de verdade têm atraso e limites próprios: isto mede o NOSSO lado
(organização, paralelismo, gravação), não a velocidade do DeepL ou do Google.
"""

import argparse
import random
import resource
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_core import make_mod  # noqa: E402

from kenshi_quick_translator.core import Options, build_translation, translate_project  # noqa: E402
from kenshi_quick_translator.markers import markers_match  # noqa: E402
from kenshi_quick_translator.memory import TranslationMemory  # noqa: E402
from kenshi_quick_translator.project import AUTO, Project  # noqa: E402
from kenshi_quick_translator.providers import Simulated  # noqa: E402
from kenshi_quick_translator.session import Session  # noqa: E402
from kenshi_quick_translator.config import Config  # noqa: E402

WORDS = ("the caravan storm friend bandit hive swamp holy nation blade hunger desert trade slave "
         "outlaw road campfire merchant shek ruin thief water bones rumor border guard cage").split()
MARKERS = ["/TEAMUP/", "/GETLOST/", "/BROTHER/", "/TRASH/", "/BASTARD/s", "/OUTLANDER/"]


def make_lines(n: int, dup: float, seed: int = 7) -> list[str]:
    rnd = random.Random(seed)
    pool: list[str] = []
    out: list[str] = []
    for i in range(n):
        if pool and rnd.random() < dup:
            out.append(rnd.choice(pool))  # frase repetida, comum em mods de diálogo
            continue
        k = rnd.randint(3, 40)
        words = [rnd.choice(WORDS) for _ in range(k)]
        if rnd.random() < 0.12:
            words.insert(rnd.randint(0, k), rnd.choice(MARKERS))
        text = " ".join(words).capitalize() + f" ({i})."
        pool.append(text)
        out.append(text)
    return out


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--texts", type=int, default=50000)
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--workers", default="6")
    ap.add_argument("--dup", type=float, default=0.25, help="fração de textos repetidos")
    args = ap.parse_args()

    lines = make_lines(args.texts, args.dup)
    unique = len(set(lines))
    print(f"Mod sintético: {args.texts} textos, {unique} diferentes ({args.dup:.0%} repetidos), "
          f"atraso simulado por pedido: {args.delay}s")

    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        t = time.monotonic()
        raw = make_mod(lines, "Big.mod")
        mod_path = work / "Big.mod"
        mod_path.write_bytes(raw)
        print(f"  montar o .mod            : {time.monotonic() - t:6.2f}s  ({len(raw) / 1e6:.1f} MB)")

        t = time.monotonic()
        proj0 = Project.from_mod_file(mod_path, work / "proj")
        print(f"  ler o mod e criar projeto: {time.monotonic() - t:6.2f}s  ({len(proj0.units)} unidades)")

        base = None
        for w in [int(x) for x in args.workers.split(",")]:
            proj = Project.from_mod_file(mod_path, work / f"proj{w}")
            prov = Simulated(delay=args.delay)
            mem = TranslationMemory()  # vazia: mede só o serviço
            t = time.monotonic()
            rep = translate_project(proj, prov, memory=mem, options=Options(workers=w, save_interval=5.0))
            el = time.monotonic() - t
            done = sum(1 for u in proj.units if u.status == AUTO)
            bad = sum(1 for u in proj.units if u.status == AUTO and not markers_match(u.source, u.translation))
            sent = sum(len(c) for c in prov.calls)
            base = base or el
            print(f"  traduzir com {w:2d} parte(s) : {el:6.2f}s  | {len(prov.calls)} pedidos, {sent} textos enviados "
                  f"(de {args.texts}) | {done} prontos | marcadores quebrados: {bad} | "
                  f"{base / el:4.1f}x em relação à 1ª medição | {args.texts / el * 60:,.0f} textos/min")
            assert done == args.texts - sum(1 for u in proj.units if u.status != AUTO), "algo ficou sem tradução"
            assert bad == 0
            last = proj

        t = time.monotonic()
        last.save()
        sz = last.path.stat().st_size / 1e6
        print(f"  salvar o projeto         : {time.monotonic() - t:6.2f}s  ({sz:.1f} MB)")
        t = time.monotonic()
        Project.load(last.path)
        print(f"  reabrir o projeto        : {time.monotonic() - t:6.2f}s")

        t = time.monotonic()
        res = build_translation(last, mod_path, work / "out")
        print(f"  gerar + conferir o mod   : {time.monotonic() - t:6.2f}s  ({res.path.stat().st_size / 1e6:.1f} MB, "
              f"{res.written} textos, problemas: {len(res.problems)})")
        assert not res.problems, res.problems[:3]

        cfg = Config()
        cfg.save = lambda path=None: None
        s = Session(cfg, workdir=work / "dados")
        s.project = last
        t = time.monotonic()
        a = s.visible_units("todos", "")
        b = s.visible_units("todos", "caravan")
        c = s.visible_units("atencao", "")
        print(f"  filtrar/buscar na tela   : {time.monotonic() - t:6.2f}s  (todos={len(a)}, busca={len(b)}, conferir={len(c)})")
        s.close()
    print(f"  pico de memória do processo: {rss_mb():.0f} MB")


if __name__ == "__main__":
    main()
