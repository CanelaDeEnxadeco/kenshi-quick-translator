"""
Motor de tradução: traduz um projeto, gera o mod de tradução e confere o
resultado. Nenhuma tradução que perca um marcador do jogo é gravada.

Velocidade: cada texto repetido vai ao serviço uma vez só; o que já foi
traduzido antes sai da memória; o resto vai em lotes, vários ao mesmo tempo.
O número de lotes simultâneos baixa sozinho se o serviço reclamar de excesso
de pedidos e volta a subir quando ele aceita de novo.
"""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from kenshi_translator_toolkit import TypeCode, dump, load
from kenshi_translator_toolkit import apply as _apply_units
from kenshi_translator_toolkit import build_translation_mod as _build_override

from .glossary import Glossary
from .locate import ORIGINAL_SUFFIX, real_mod_name
from .langdetect import detect_text, same_language
from .markers import Masked, has_letters, markers_match, mask
from .memory import TranslationMemory
from .project import ATTENTION, AUTO, IGNORED, PENDING, REVIEWED, Project, Unit
from .providers import Provider, ProviderError

ProgressFn = Callable[[int, int, str], None]

MAX_ATTEMPTS = 5  # tentativas por lote quando o serviço reclama de excesso de pedidos
BACKOFF_BASE = 1.5  # segundos; dobra a cada tentativa (testes colocam 0)
MAX_WORKERS = 12


class ProviderBroken(Exception):
    """O serviço falhou várias vezes seguidas; melhor parar do que insistir."""


@dataclass
class Options:
    chunk_size: int | None = None  # padrão: o máximo do serviço
    workers: int = 3  # lotes ao mesmo tempo (1 a 12)
    keep_character_names: bool = True  # nomes de personagens ficam como estão
    retranslate: bool = False  # refaz 'automatica' e 'atencao' (nunca 'revisada')
    only_attention: bool = False  # segunda passada: só os textos em 'atencao'; não piora o que já havia
    extra_patterns: tuple[str, ...] = ()
    max_consecutive_failures: int = 3
    on_message: Callable[[str], None] | None = None  # avisos ao vivo (a janela mostra na hora)
    notify_switch: bool = True  # avisar (em Report.messages) quando o agregado troca de serviço
    save_interval: float = 5.0  # segundos entre gravações do projeto (mods enormes)
    # Modo "vários idiomas de origem": cada texto tem o idioma detectado separadamente.
    multi_source: bool = False
    source_langs: tuple[str, ...] = ()  # idiomas que o usuário diz haver no mod (dica; vazio = qualquer)


@dataclass
class Report:
    translated: int = 0
    from_memory: int = 0
    ignored: int = 0
    attention: int = 0
    failed: int = 0
    cancelled: bool = False
    messages: list[str] = field(default_factory=list)
    field_notes: list[str] = field(default_factory=list)  # campos deixados em inglês por parecerem código
    languages: dict[str, int] = field(default_factory=dict)  # só no modo "vários idiomas"
    seconds: float = 0.0
    workers_used: int = 1  # onde o controle automático terminou


class _Cancelled(Exception):
    pass


class Throttle:
    """Limita quantos lotes rodam ao mesmo tempo e ajusta o limite conforme o serviço responde."""

    def __init__(self, limit: int) -> None:
        self.max = max(1, min(MAX_WORKERS, limit))
        self.limit = self.max
        self._active = 0
        self._ok = 0
        self._cond = threading.Condition()

    def acquire(self, cancel: threading.Event) -> bool:
        with self._cond:
            while self._active >= self.limit:
                if cancel.is_set():
                    return False
                self._cond.wait(0.2)
            if cancel.is_set():
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._cond:
            self._active -= 1
            self._cond.notify_all()

    def on_success(self) -> None:
        with self._cond:
            self._ok += 1
            if self._ok >= 5 and self.limit < self.max:
                self.limit += 1
                self._ok = 0
                self._cond.notify_all()

    def on_throttled(self) -> None:
        with self._cond:
            self.limit = max(1, self.limit // 2)
            self._ok = 0


class _Saver:
    """Grava o projeto de tempos em tempos (não a cada lote: em mods enormes isso pesa)."""

    def __init__(self, project: Project, interval: float) -> None:
        self.project, self.interval = project, interval
        self._last = time.monotonic()

    def maybe(self) -> None:
        if self.project.path is not None and time.monotonic() - self._last >= self.interval:
            self.now()

    def now(self) -> None:
        if self.project.path is not None:
            self.project.save()
        self._last = time.monotonic()


# ---------------------------------------------------------------- traduzir
def translate_project(
    project: Project,
    provider: Provider,
    *,
    glossary: Glossary | None = None,
    memory: TranslationMemory | None = None,
    options: Options | None = None,
    progress: ProgressFn | None = None,
    cancel: threading.Event | None = None,
) -> Report:
    opts = options or Options()
    report = Report()
    started = time.monotonic()
    cancel = cancel or threading.Event()
    notify = progress or (lambda done, total, msg: None)
    target = project.target_lang
    saver = _Saver(project, opts.save_interval)

    fr = getattr(project, "field_report", None)
    if fr is not None:
        report.field_notes = fr.lines()
    todo = [u for u in project.units if _wants(u, opts)]
    total = len(todo)
    done = 0
    if not todo:
        return report

    # 1) o que não precisa de serviço: sem letras, nomes, já no idioma de destino, memória
    lang_cache: dict[str, str] = {}
    pending: list[Unit] = []
    for u in todo:
        if not has_letters(u.source):
            _set(u, "", IGNORED, "sem letras para traduzir")
            report.ignored += 1
            done += 1
            continue
        if opts.keep_character_names and u.typecode == TypeCode.CHARACTER and u.field == "":
            _set(u, "", IGNORED, "nome de personagem mantido")
            report.ignored += 1
            done += 1
            continue
        if opts.multi_source:
            code = lang_cache.get(u.source)
            if code is None:
                code = lang_cache[u.source] = detect_text(u.source)
            u.lang = code
            if code != "und" and same_language(code, target):
                _set(u, "", IGNORED, "já está no idioma de destino")
                report.ignored += 1
                done += 1
                continue
        pending.append(u)

    remembered = memory.get_many({u.source for u in pending}, target) if memory else {}
    queue: dict[str, list[Unit]] = {}
    for u in pending:
        text = remembered.get(u.source)
        if text and markers_match(u.source, text):
            _set(u, text, AUTO, "da memória de tradução")
            report.from_memory += 1
            done += 1
        else:
            queue.setdefault(u.source, []).append(u)
    if opts.multi_source:
        for u in todo:
            if u.lang:
                report.languages[u.lang] = report.languages.get(u.lang, 0) + 1
    notify(done, total, "Preparando")
    saver.now()

    # 2) o que precisa de serviço: textos únicos, mascarados, em lotes, por idioma de origem
    masked = {src: mask(src, glossary, opts.extra_patterns) for src in queue}
    groups: dict[str, list[str]] = {}
    for src, units in queue.items():
        groups.setdefault(_source_group(units[0], project, opts), []).append(src)
    size = max(1, opts.chunk_size or provider.max_batch)
    chunks: list[tuple[str, list[str]]] = []
    for lang, sources in groups.items():
        chunks += [(lang, sources[i : i + size]) for i in range(0, len(sources), size)]

    if hasattr(provider, "bind_cancel"):  # agregado: espera cancelável e avisos em português
        provider.bind_cancel(cancel)
        def _event(m: str) -> None:
            if m not in report.messages[-3:]:
                report.messages.append(m)
            if opts.on_message:
                opts.on_message(m)

        provider.on_event = _event if opts.notify_switch else None
    throttle = Throttle(max(opts.workers, min(12, getattr(provider, "parallel_hint", 0))))
    failures = 0
    pool = ThreadPoolExecutor(max_workers=throttle.max)
    try:
        futures = {
            pool.submit(_job, provider, lang, chunk, masked, target, cancel, throttle): chunk
            for lang, chunk in chunks
        }
        for fut in as_completed(futures):
            chunk = futures[fut]
            if cancel.is_set():
                report.cancelled = True
                break
            try:
                results = fut.result()
                failures = 0
            except _Cancelled:
                report.cancelled = True
                break
            except ProviderError as e:
                failures += 1
                count = sum(len(queue[s]) for s in chunk)
                report.failed += count
                report.messages.append(str(e))
                for s in chunk:
                    for u in queue[s]:
                        u.note = f"falhou: {e}"
                if failures >= opts.max_consecutive_failures:
                    saver.now()
                    raise ProviderBroken(
                        f"{provider.label} falhou {failures} vezes seguidas: {e}. "
                        "Troque de serviço ou tente mais tarde. O que já foi traduzido foi salvo."
                    ) from e
                done += count
                notify(done, total, "Falha em um lote, seguindo")
                continue

            to_remember: list[tuple[str, str]] = []
            for src, (text, status, note) in results.items():
                for u in queue[src]:
                    if opts.only_attention and (text is None or status == ATTENTION):
                        report.attention += 1  # segunda passada não melhorou: mantém o que já havia
                    elif text is None:
                        _set(u, "", ATTENTION, note)
                        report.attention += 1
                    else:
                        _set(u, text, status, note)
                        if status == ATTENTION:
                            report.attention += 1
                        else:
                            report.translated += 1
                    done += 1
                if text is not None and status == AUTO:
                    to_remember.append((src, text))
            if memory and to_remember:
                memory.put_many(to_remember, target, origin=provider.name)
            saver.maybe()
            notify(done, total, "Traduzindo")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        report.workers_used = throttle.limit

    saver.now()
    report.seconds = time.monotonic() - started
    return report


def _wants(u: Unit, opts: Options) -> bool:
    if opts.only_attention:
        return u.status == ATTENTION
    if u.status == PENDING:
        return True
    return opts.retranslate and u.status in (AUTO, ATTENTION)


def _set(u: Unit, text: str, status: str, note: str = "") -> None:
    u.translation, u.status, u.note = text, status, note


def _source_group(unit: Unit, project: Project, opts: Options) -> str:
    """Idioma de origem enviado ao serviço para este texto."""
    if not opts.multi_source:
        return project.source_lang
    code = unit.lang
    if code in ("", "und"):
        return "auto"
    if opts.source_langs and not any(same_language(code, s) for s in opts.source_langs):
        return "auto"  # idioma que o usuário não listou: deixa o serviço decidir
    return code


def _job(
    provider: Provider,
    lang: str,
    chunk: list[str],
    masked: dict[str, Masked],
    target: str,
    cancel: threading.Event,
    throttle: Throttle,
) -> dict[str, tuple[str | None, str, str]]:
    """Um lote, respeitando o limite de simultâneos e tentando de novo se o serviço reclamar."""
    for attempt in range(MAX_ATTEMPTS):
        if not throttle.acquire(cancel):
            raise _Cancelled()
        try:
            result = _run_chunk(provider, chunk, masked, lang, target, cancel)
            throttle.on_success()
            return result
        except ProviderError as e:
            if not e.retryable or attempt == MAX_ATTEMPTS - 1:
                raise
            throttle.on_throttled()
        finally:
            throttle.release()
        if cancel.wait(BACKOFF_BASE * (2**attempt)):  # espera fora da vaga; para na hora se cancelar
            raise _Cancelled()
    raise _Cancelled()  # inalcançável


def _run_chunk(
    provider: Provider,
    chunk: list[str],
    masked: dict[str, Masked],
    source_lang: str,
    target: str,
    cancel: threading.Event,
) -> dict[str, tuple[str | None, str, str]]:
    """
    Traduz um lote. Devolve {original: (traducao|None, status, nota)}.

    Tentativas, nesta ordem, só para os textos cujo marcador se perdeu:
    1. fichas alfanuméricas; 2. fichas em forma de tag; 3. tradução por
    partes (os trechos entre marcadores são traduzidos separados).
    """
    if cancel.is_set():
        raise _Cancelled()
    results: dict[str, tuple[str | None, str, str]] = {}

    out = [g or "" for g in provider.translate_batch([masked[s].text_for("alnum") for s in chunk], source_lang, target)]
    retry: list[str] = []
    for src, got in zip(chunk, out):
        text, problems = masked[src].restore(got, "alnum")
        if not got.strip():
            retry.append(src)
        elif problems:
            retry.append(src)
        else:
            results[src] = (text, AUTO, "")

    if retry and not cancel.is_set():
        out = [g or "" for g in provider.translate_batch([masked[s].text_for("tag") for s in retry], source_lang, target)]
        retry2: list[str] = []
        for src, got in zip(retry, out):
            text, problems = masked[src].restore(got, "tag")
            if not got.strip() or problems:
                retry2.append(src)
            else:
                results[src] = (text, AUTO, "")
        retry = retry2

    if retry and not cancel.is_set():
        # Por partes: junta todos os trechos de todos os textos numa chamada só.
        flat: list[str] = []
        spans: list[tuple[str, int, int]] = []
        for src in retry:
            parts = masked[src].text_pieces()
            start = len(flat)
            flat.extend(parts)
            spans.append((src, start, len(flat)))
        translatable = [i for i, p in enumerate(flat) if has_letters(p)]
        translated = list(flat)
        if translatable:
            got = provider.translate_batch([flat[i] for i in translatable], source_lang, target)
            for i, g in zip(translatable, got):
                translated[i] = _keep_edges(flat[i], g or flat[i])
        for src, a, b in spans:
            joined = masked[src].join_pieces(translated[a:b])
            if markers_match(src, joined) and joined.strip():
                results[src] = (joined, ATTENTION, "traduzido por partes: confira a fluidez")
            else:
                results[src] = (None, ATTENTION, "o serviço estragou os marcadores; mantido o original")
    return results


def _keep_edges(original: str, translated: str) -> str:
    """Mantém os espaços do começo e do fim do trecho, que o serviço costuma cortar."""
    lead = original[: len(original) - len(original.lstrip())]
    trail = original[len(original.rstrip()) :]
    return lead + translated.strip() + trail


def analyze_languages(project: Project) -> dict[str, int]:
    """
    Detecta o idioma de cada texto do projeto (sem traduzir nada) e devolve
    quantos textos há por idioma. Serve para mostrar ao usuário o que o mod tem.
    """
    cache: dict[str, str] = {}
    for u in project.units:
        if u.field == "" or not has_letters(u.source):
            u.lang = ""
            continue
        code = cache.get(u.source)
        if code is None:
            code = cache[u.source] = detect_text(u.source)
        u.lang = code
    return project.language_counts()


# ---------------------------------------------------------------- gerar mod
# a marca atual e a antiga (o programa se chamava "Kenshi Tradutor" até a 0.6.2): mods já instalados continuam reconhecidos
_MARK_NAMES = ("Kenshi Quick Translator", "Kenshi Tradutor")
_MARK_RE = re.compile(r"\s*\[(?:Kenshi Quick Translator|Kenshi Tradutor): [^\]]*\]\s*$")


MODE_FULL = "completo"  # cópia completa, MESMO nome do original, ocupa o lugar dele
MODE_DEPENDENT = "dependente"  # arquivo pequeno "Nome IDIOMA.mod" que depende do original


def translation_filename(mod_name: str, target_lang: str = "", dependent: bool = False) -> str:
    """
    Modo completo: o mesmo nome do original (o idioma não entra no nome).
    Modo dependente: "Nome IDIOMA.mod" (precisa de nome diferente, senão dependeria de si mesmo).
    """
    name = real_mod_name(mod_name)
    stem = name[:-4] if name.lower().endswith(".mod") else name
    return f"{stem} {target_lang.upper()}.mod" if dependent and target_lang else f"{stem}.mod"


@dataclass
class BuildResult:
    path: Path
    written: int
    problems: list[str]


def _enc_len(text: str) -> int:
    return len((text or "").encode("utf-8", errors="surrogateescape"))


def set_description(mod, new_description: str) -> None:
    """
    Troca a descrição do mod. Nos mods de cabeçalho estendido (tipo 17) o tamanho do cabeçalho
    (`header_length`) conta os bytes da descrição: se ela muda de tamanho, ele precisa mudar junto,
    senão o Kenshi/FCS leem o arquivo deslocado e dizem "Corrupt mod file".
    """
    delta = _enc_len(new_description) - _enc_len(mod.description)
    mod.description = new_description
    if mod.header_length is not None:
        mod.header_length += delta


def build_translation(
    project: Project,
    mod_path: str | Path,
    out_dir: str | Path,
    description: str | None = None,
    mode: str = MODE_FULL,
) -> BuildResult:
    """
    Gera o mod traduzido e confere o arquivo. Nunca altera o original.
      - mode="completo" (padrão): CÓPIA COMPLETA do original com os textos traduzidos, com o mesmo
        nome do original (o nome não muda ao trocar de idioma e o traduzido ocupa o lugar do
        original no jogo). Não depende do original.
      - mode="dependente": só o que mudou, em "Nome IDIOMA.mod", declarando o original como
        dependência (o Kenshi carrega o original e depois a tradução por cima).
    """
    mod_path = Path(mod_path)
    mod = load(mod_path.read_bytes())
    dependent = mode == MODE_DEPENDENT
    if dependent:
        desc = description or f"Tradução {project.target_lang} de {real_mod_name(project.mod_name)} (Kenshi Quick Translator)"
        mod = _build_override(mod, project.toolkit_units(), real_mod_name(project.mod_name), description=desc)
    else:
        _apply_units(mod, project.toolkit_units())
        mark = f"[Kenshi Quick Translator: {project.target_lang}]"
        set_description(mod, (_MARK_RE.sub("", mod.description or "") + "\n" + mark).strip())
    data = dump(mod)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / translation_filename(project.mod_name, project.target_lang, dependent)
    if out_path.resolve() == mod_path.resolve():
        raise ValueError("A pasta de saída é a do próprio mod original: escolha outra pasta para não sobrescrevê-lo.")
    out_path.write_bytes(data)

    written = sum(1 for u in project.units if u.translation.strip())
    return BuildResult(out_path, written, verify_output(out_path, project))


def verify_output(out_path: str | Path, project: Project) -> list[str]:
    """Lê o arquivo gerado de volta e confere. Lista vazia = tudo certo."""
    problems: list[str] = []
    raw = Path(out_path).read_bytes()
    try:
        mod = load(raw)
    except Exception as e:  # noqa: BLE001
        return [f"o arquivo gerado não pôde ser lido de volta: {e}"]
    if dump(mod) != raw:
        problems.append("o arquivo gerado não é idêntico ao reescrever (formato inconsistente)")
    deps = [d.strip() for d in mod.dependencies.split(",")]
    original = real_mod_name(project.mod_name)
    if Path(out_path).name.lower() == original.lower():  # modo completo
        if original in deps:
            problems.append("o mod traduzido depende de si mesmo (o nome é o mesmo do original)")
    elif original not in deps:  # modo dependente
        problems.append("o mod de tradução não declara o original como dependência (ordem de carga não garantida)")

    # tudo o que o arquivo gerado contém (nome e campos de texto de cada registro)
    found: dict[tuple[str, str], str] = {}
    for rec in mod.records:
        found[(rec.string_id, "")] = rec.name
        for key, value in rec.strings:
            found.setdefault((rec.string_id, key), value)
    for u in project.units:
        if not u.translation.strip():
            continue
        if found.get(u.key) != u.translation:
            problems.append(f"texto não encontrado no arquivo gerado: {u.string_id}/{u.field or 'nome'}")
        if not markers_match(u.source, u.translation):
            problems.append(f"marcadores diferentes em {u.string_id}/{u.field or 'nome'}")
    return problems


# ---------------------------------------------------------------- instalar
def add_to_mods_cfg(cfg_path: str | Path, mod_filename: str, after: str) -> bool:
    """
    Põe `mod_filename` em mods.cfg logo depois de `after` (o mod original).
    Faz backup antes. Devolve False se já estava lá (nada a fazer).
    """
    import shutil

    cfg_path = Path(cfg_path)
    raw = cfg_path.read_bytes() if cfg_path.exists() else b""
    text = raw.decode("utf-8", errors="surrogateescape")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    if mod_filename in (ln.strip() for ln in lines):
        return False
    if cfg_path.exists():
        shutil.copy2(cfg_path, cfg_path.with_name(f"{cfg_path.name}.bak-{time.strftime('%Y%m%d%H%M%S')}"))

    idx = next((i for i, ln in enumerate(lines) if ln.strip() == after), None)
    if idx is None:
        lines.append(mod_filename)
    else:
        lines.insert(idx + 1, mod_filename)
    out = nl.join(lines) + nl
    cfg_path.write_bytes(out.encode("utf-8", errors="surrogateescape"))
    return True


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tga", ".dds", ".img"}


def copy_mod_images(source_dir: str | Path, dest_dir: str | Path, original_stem: str, new_stem: str) -> list[str]:
    """
    Copia a imagem/ícone do mod original (o que aparece na lista de mods do Kenshi) para a pasta
    do mod de tradução. Se o nome da imagem leva o nome do mod, ele passa a levar o nome novo.
    Só imagens: os outros arquivos do mod original NÃO são copiados.
    """
    import shutil

    source_dir, dest_dir = Path(source_dir), Path(dest_dir)
    copied: list[str] = []
    if not source_dir.is_dir() or source_dir.resolve() == dest_dir.resolve():
        return copied
    for f in sorted(source_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
            name = f.name.replace(original_stem, new_stem) if original_stem and original_stem in f.stem else f.name
            shutil.copy2(f, dest_dir / name)
            copied.append(name)
    return copied


def copy_mod_folder(source_dir: str | Path, dest_dir: str | Path, original_stem: str, new_stem: str,
                    skip: set[str] | None = None) -> int:
    """
    Copia TUDO da pasta do mod original (.info, subpastas com modelos/texturas, imagens...) para a
    pasta do mod de tradução. Só o(s) arquivo(s) .mod NÃO são copiados: no lugar deles fica o .mod
    traduzido. Imagens com o nome do mod no nome ganham o nome novo. Devolve quantos arquivos copiou.
    """
    import shutil

    source_dir, dest_dir = Path(source_dir), Path(dest_dir)
    if not source_dir.is_dir() or source_dir.resolve() == dest_dir.resolve():
        return 0
    skip = {n.lower() for n in (skip or set())}
    count = 0
    for f in sorted(source_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() == ".mod" or f.name.lower() in skip:
            continue
        rel = f.relative_to(source_dir)
        name = rel.name
        if len(rel.parts) == 1 and f.suffix.lower() in IMAGE_EXTS and original_stem and original_stem in f.stem:
            name = name.replace(original_stem, new_stem)
        target = dest_dir / rel.parent / name
        if dest_dir.resolve() in f.resolve().parents:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        count += 1
    return count


@dataclass
class InstallInfo:
    dest: Path  # arquivo instalado
    cfg_changed: bool  # mods.cfg foi alterado
    backup: Path | None = None  # onde está o original guardado (None: modo dependente)
    backup_created: bool = False  # True se o backup foi feito AGORA (antes não existia)
    replaced_translation: bool = False  # havia uma tradução anterior (outro idioma) no lugar


def install_translation_info(
    kenshi_dir: str | Path, built: str | Path, original_name: str, source_dir: str | Path | None = None
) -> InstallInfo:
    """
    Instala o mod traduzido em Kenshi/mods/<nome>/<nome>.mod (mesmo nome do original) e garante que
    ele está ativo em data/mods.cfg. Se já existe um .mod ali (o original, ou uma tradução anterior),
    o ORIGINAL é guardado uma vez como "<nome>.mod.original" antes de ser trocado; uma tradução
    anterior (outro idioma) é simplesmente substituída.
    """
    import shutil

    kenshi_dir = Path(kenshi_dir)
    built = Path(built)
    name = built.name
    original = translation_filename(original_name)
    dependent = name.lower() != original.lower()  # "Nome IDIOMA.mod": modo dependente, pasta própria
    dest_dir = kenshi_dir / "mods" / Path(name).stem
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    info = InstallInfo(dest=dest, cfg_changed=False)
    if not dependent:
        backup = dest.with_name(dest.name + ORIGINAL_SUFFIX)
        if dest.exists():
            ours = _is_ours(dest)
            info.replaced_translation = ours
            if not backup.exists() and not ours:
                shutil.copy2(dest, backup)
                info.backup_created = True
        if backup.exists():
            info.backup = backup
    if source_dir is not None:
        copy_mod_folder(source_dir, dest_dir, Path(original).stem, Path(name).stem)
    shutil.copy2(built, dest)
    info.cfg_changed = add_to_mods_cfg(kenshi_dir / "data" / "mods.cfg", name, after=original)
    return info


def install_translation(
    kenshi_dir: str | Path, built: str | Path, original_name: str, source_dir: str | Path | None = None
) -> tuple[Path, bool]:
    """Como install_translation_info, mas devolve só (arquivo instalado, mods.cfg mudou)."""
    info = install_translation_info(kenshi_dir, built, original_name, source_dir)
    return info.dest, info.cfg_changed


def _is_ours(mod_file: Path) -> bool:
    """True se o .mod já foi gerado por este programa (tem a marca na descrição): não é um original."""
    try:
        desc = load(mod_file.read_bytes()).description
        return any(f"[{n}:" in desc for n in _MARK_NAMES)
    except Exception:  # noqa: BLE001 - arquivo ilegível: trata como original e guarda backup
        return False


def copy_mod_to_game(mod_file: str | Path, kenshi_dir: str | Path) -> tuple[Path, int]:
    """
    "Copiar para a pasta do jogo" (como o Copy to GameDir do original): copia a pasta do mod do
    Workshop para Kenshi/mods/<nome do mod>/. Só LÊ o Workshop; o destino é sobrescrito.
    Devolve (pasta de destino, arquivos copiados).
    """
    import shutil

    mod_file = Path(mod_file)
    src = mod_file.parent
    dest = Path(kenshi_dir) / "mods" / mod_file.stem
    if src.resolve() == dest.resolve():
        raise ValueError("O mod já está na pasta do jogo.")
    count = 0
    for f in src.rglob("*"):
        if f.is_file():
            target = dest / f.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            count += 1
    if not count:
        raise FileNotFoundError(f"Nada para copiar em {src}")
    return dest, count
