"""Linha de comando. A interface gráfica usa exatamente as mesmas funções."""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

from . import __version__
from .config import Config, glossary_path, memory_path, projects_dir
from .core import Options, ProviderBroken, analyze_languages, build_translation, install_translation, translate_project
from .glossary import Glossary
from .langdetect import detect_language, lang_name
from .session import present_languages
from .locate import find_kenshi, scan_mods
from .memory import TranslationMemory
from .project import Project
from .providers import LANGUAGES, ProviderError, make_provider


def _load_glossary(path: str | None) -> Glossary:
    if path:
        return Glossary.load(path)
    user = glossary_path()
    if user.exists():
        return Glossary.load(user)
    return Glossary.default()


def _open_project(args: argparse.Namespace) -> Project:
    workdir = Path(args.workdir) if args.workdir else projects_dir()
    return Project.from_mod_file(args.mod, workdir, target_lang=args.to, source_lang=args.source)


def cmd_info(args: argparse.Namespace) -> int:
    proj = _open_project(args)
    lang, conf = detect_language(u.source for u in proj.units if u.field != "")
    counts = analyze_languages(proj)
    st = proj.stats()
    print(f"Mod: {proj.mod_name}")
    print(f"Textos traduzíveis: {st['total']}")
    print(f"Idioma dominante: {lang} (confiança {conf:.0%})")
    print("Idiomas texto a texto: " + (", ".join(f"{lang_name(k)} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) or "nenhum"))
    if len(present_languages(counts)) > 1:
        print("Este mod tem mais de um idioma. Use: translate --multi (ou --sources "
              + ",".join(present_languages(counts)) + ")")
    print(
        f"Estado: {st['pendente']} pendentes, {st['automatica']} automáticos, "
        f"{st['revisada']} revisados, {st['atencao']} para conferir, {st['ignorada']} ignorados"
    )
    return 0


def cmd_translate(args: argparse.Namespace) -> int:
    cfg = Config.load()
    key = args.key or cfg.api_key
    try:
        provider = make_provider(args.provider, key, args.url or cfg.server_url, cfg.free_order, cfg.services, cfg.use_free, cfg.spread)
    except (ProviderError, ValueError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2

    proj = _open_project(args)
    glossary = _load_glossary(args.glossary)
    memdb = Path(args.workdir) / "memoria.sqlite" if args.workdir else memory_path()
    memory = TranslationMemory(memdb)
    sources = tuple(s.strip() for s in (args.sources or "").split(",") if s.strip())
    opts = Options(
        retranslate=args.retranslate,
        keep_character_names=not args.traduzir_nomes,
        workers=args.workers,
        multi_source=args.multi or bool(sources),
        source_langs=sources,
    )

    def progress(done: int, total: int, msg: str) -> None:
        print(f"\r{msg}: {done}/{total}", end="", flush=True)

    try:
        report = translate_project(proj, provider, glossary=glossary, memory=memory, options=opts,
                                   progress=progress, cancel=threading.Event())
    except ProviderBroken as e:
        print(f"\n{e}", file=sys.stderr)
        return 3
    finally:
        memory.close()
    print()
    print(
        f"Traduzidos: {report.translated} | da memória: {report.from_memory} | "
        f"ignorados: {report.ignored} | para conferir: {report.attention} | falhas: {report.failed}"
    )
    for m in dict.fromkeys(report.messages):
        print(f"  aviso: {m}")
    for n in report.field_notes:
        print(f"  campo deixado em inglês: {n}")

    out_dir = Path(args.out) if args.out else Path.cwd()  # nunca ao lado do original (pode ser a pasta do Workshop)
    result = build_translation(proj, args.mod, out_dir, mode="dependente" if args.dependent else "completo")
    print(f"Mod de tradução: {result.path} ({result.written} textos)")
    if result.problems:
        print("PROBLEMAS na conferência do arquivo gerado:")
        for p in result.problems:
            print(f"  - {p}")
        return 4
    print("Conferência do arquivo gerado: ok")

    if args.install:
        dirs = find_kenshi(args.kenshi or Config.load().kenshi_dir)
        if dirs.kenshi is None:
            print("Não achei o Kenshi. Use --kenshi CAMINHO.", file=sys.stderr)
            return 5
        dest, changed = install_translation(dirs.kenshi, result.path, proj.mod_name)
        print(f"Instalado em {dest}")
        print("mods.cfg atualizado (com backup)." if changed else "mods.cfg já tinha o mod.")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = Config.load()
    dirs = find_kenshi(args.kenshi or cfg.kenshi_dir, cfg.workshop_dir)
    if dirs.kenshi is None:
        print("Kenshi não encontrado. Use --kenshi CAMINHO.")
        return 5
    print(f"Kenshi: {dirs.kenshi} ({dirs.how})")
    print(f"Workshop: {dirs.workshop or 'não encontrado'}")
    for m in scan_mods(dirs):
        print(f"  [{m.source:8}] {m.name}  ({m.size / 1024:.0f} KB)  {m.path}")
    return 0


def cmd_po_export(args: argparse.Namespace) -> int:
    proj = _open_project(args)
    Path(args.out).write_text(proj.export_po(), encoding="utf-8")
    print(f"PO salvo em {args.out}")
    return 0


def cmd_po_import(args: argparse.Namespace) -> int:
    proj = _open_project(args)
    n = proj.import_po(Path(args.po).read_text(encoding="utf-8"))
    proj.save()
    print(f"{n} traduções importadas")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .gui import run
    except ImportError as e:
        print(
            "Não consegui abrir a janela: o Tkinter não está instalado "
            f"({e}). No Windows ele já vem com o Python; no Linux instale o pacote python3-tk. "
            "Enquanto isso, use a linha de comando: kenshi-quick-translator --help",
            file=sys.stderr,
        )
        return 6
    run()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kenshi-quick-translator", description="Traduz mods do Kenshi.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("mod", help="arquivo .mod")
        sp.add_argument("--to", default="pt-BR", choices=[k for k in LANGUAGES if k != "auto"], help="idioma de destino")
        sp.add_argument("--source", default="auto", choices=list(LANGUAGES), help="idioma de origem")
        sp.add_argument("--workdir", help="pasta dos projetos e da memória (padrão: pasta do programa)")

    s = sub.add_parser("info", help="mostra textos e idioma detectado")
    common(s)
    s.set_defaults(fn=cmd_info)

    s = sub.add_parser("translate", help="traduz e gera o mod de tradução")
    common(s)
    s.add_argument("--provider", default="agregado", choices=["agregado", "deepl", "google-cloud", "libretranslate", "google-free", "google2", "bing", "microsoft", "yandex", "simulado"])
    s.add_argument("--key", help="chave da API (ou variável KENSHI_TRADUTOR_KEY)")
    s.add_argument("--url", help="endereço do servidor (LibreTranslate)")
    s.add_argument("--glossary", help="arquivo de glossário JSON")
    s.add_argument("--out", help="pasta de saída (padrão: pasta atual)")
    s.add_argument("--retranslate", action="store_true", help="refaz o que já foi traduzido automaticamente")
    s.add_argument("--dependent", action="store_true", help="gera só o que mudou em \"Nome IDIOMA.mod\", dependente do original (padrão: cópia completa com o mesmo nome)")
    s.add_argument("--traduzir-nomes", action="store_true", help="também traduz nomes de personagens")
    s.add_argument("--workers", type=int, default=3, choices=range(1, 13), metavar="1-12",
                   help="lotes de tradução ao mesmo tempo (padrão 3; baixa sozinho se o serviço reclamar)")
    s.add_argument("--multi", action="store_true", help="mod com mais de um idioma de origem: detecta o idioma de cada texto")
    s.add_argument("--sources", help="idiomas presentes no mod, separados por vírgula (ex.: en,zh); liga o modo --multi")
    s.add_argument("--install", action="store_true", help="instala em Kenshi/mods e ativa em mods.cfg")
    s.add_argument("--kenshi", help="pasta do Kenshi")
    s.set_defaults(fn=cmd_translate)

    s = sub.add_parser("scan", help="lista os mods instalados")
    s.add_argument("--kenshi", help="pasta do Kenshi")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("po-export", help="exporta para PO (Poedit)")
    common(s)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_po_export)

    s = sub.add_parser("po-import", help="importa traduções de um PO")
    common(s)
    s.add_argument("--po", required=True)
    s.set_defaults(fn=cmd_po_import)

    s = sub.add_parser("gui", help="abre a janela")
    s.set_defaults(fn=cmd_gui)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
