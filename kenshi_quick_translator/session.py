"""
Lógica da janela, sem nenhuma dependência de interface gráfica.

A janela (gui.py) só desenha e chama estes métodos; assim tudo aqui é
testável sem abrir tela.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from kenshi_translator_toolkit import collect, load

from .config import Config, app_dir, glossary_path, memory_path, projects_dir
from .core import (
    BuildResult,
    Options,
    ProgressFn,
    ProviderBroken,
    Report,
    analyze_languages,
    build_translation,
    IMAGE_EXTS,
    copy_mod_to_game,
    InstallInfo,
    install_translation_info,
    translate_project,
)
from .glossary import Glossary
from .langdetect import detect_language, detect_text, lang_name
from .locate import KenshiDirs, ModEntry, find_kenshi, is_kenshi_dir, scan_mods
from .markers import count_markers, has_letters, markers_match
from .memory import TranslationMemory
from .localefiles import build_locale_pack
from .textfiles import find_text_files, translate_text_files
from .project import ATTENTION, AUTO, IGNORED, PENDING, REVIEWED, Project, Unit, project_path, resolve_project_path
from .providers import Provider, make_provider
from .cleanup import CleanResult  # noqa: F401
from .restore import RestoreResult, has_backup, restore_original
from .review import Doubtful, UndoHistory, count_doubtful, doubtful_indexes, source_languages

FILTERS = {
    "todos": None,
    "pendente": PENDING,
    "atencao": ATTENTION,
    "automatica": AUTO,
    "revisada": REVIEWED,
    "ignorada": IGNORED,
}

# Um idioma só conta como "presente" no mod se tiver pelo menos esta parte dos textos identificados.
PRESENT_SHARE = 0.08


@dataclass
class ManyResult:
    """Resultado de um mod dentro de uma fila de vários."""

    name: str
    report: Report | None = None
    built: BuildResult | None = None
    installed: Path | None = None
    error: str = ""


def language_label(counts: dict[str, int], ui: str = "pt") -> str:
    """'Inglês (en) + Chinês (zh)' a partir da contagem por idioma, no idioma da interface `ui`
    (ignora o que é indefinido ou raro)."""
    known = {k: v for k, v in counts.items() if k != "und"}
    total = sum(known.values())
    if total == 0:
        return lang_name("und", ui)
    present = [k for k, v in sorted(known.items(), key=lambda kv: kv[1], reverse=True) if v / total >= PRESENT_SHARE]
    return " + ".join(lang_name(k, ui) for k in present)


def present_languages(counts: dict[str, int]) -> list[str]:
    """Códigos dos idiomas presentes no mod, do mais para o menos frequente."""
    known = {k: v for k, v in counts.items() if k != "und"}
    total = sum(known.values())
    if total == 0:
        return []
    return [k for k, v in sorted(known.items(), key=lambda kv: kv[1], reverse=True) if v / total >= PRESENT_SHARE]


class Session:
    def __init__(self, cfg: Config | None = None, workdir: Path | None = None) -> None:
        self.cfg = cfg or Config.load()
        self.workdir = Path(workdir) if workdir else None
        self.project: Project | None = None
        self.mod_path: Path | None = None
        self.glossary = self._load_glossary()
        self._memory: TranslationMemory | None = None
        self._profiles: dict[str, dict] | None = None
        self._profiles_lock = threading.Lock()
        self.undo = UndoHistory()
        self.last_install: InstallInfo | None = None
        self.last_locale_files = 0  # arquivos do pacote de idioma escritos na última instalação

    # ------------------------------------------------------------ recursos
    @property
    def data_folder(self) -> Path:
        return self.workdir if self.workdir else app_dir()

    @property
    def projects_folder(self) -> Path:
        return self.workdir / "projetos" if self.workdir else projects_dir()

    @property
    def memory(self) -> TranslationMemory:
        if self._memory is None:
            path = self.workdir / "memoria.sqlite" if self.workdir else memory_path()
            self._memory = TranslationMemory(path)
        return self._memory

    @property
    def glossary_file(self) -> Path:
        return self.workdir / "glossario.json" if self.workdir else glossary_path()

    def _load_glossary(self) -> Glossary:
        path = self.glossary_file
        if path.exists():
            try:
                return Glossary.load(path)
            except (OSError, ValueError):
                pass
        return Glossary.default()

    def ensure_glossary_file(self) -> Path:
        """Cria o glossário do usuário (a partir do padrão) para ele poder editar."""
        path = self.glossary_file
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            Glossary.default().save(path)
        return path

    def reload_glossary(self) -> None:
        self.glossary = self._load_glossary()

    def close(self) -> None:
        if self._memory is not None:
            self._memory.close()
            self._memory = None

    # ------------------------------------------------------------ pastas do jogo
    def locate_game(self) -> KenshiDirs:
        return find_kenshi(self.cfg.kenshi_dir, self.cfg.workshop_dir)

    def set_kenshi_dir(self, folder: str) -> bool:
        if not is_kenshi_dir(Path(folder)):
            return False
        self.cfg.kenshi_dir = folder
        self.cfg.save()
        return True

    def installed_mods(self) -> list[ModEntry]:
        return scan_mods(self.locate_game())

    # ------------------------------------------------------------ perfil de idiomas de um mod
    @staticmethod
    def detect_mod_language(path: Path) -> tuple[str, float]:
        """Idioma dominante pelo CONTEÚDO do mod (não pelo nome do arquivo)."""
        mod = load(Path(path).read_bytes())  # só lê; não cria projeto nem salva nada
        return detect_language(u.source for u in collect(mod) if u.field != "")

    def _profile_file(self) -> Path:
        return self.data_folder / "idiomas.json"

    def _load_profiles(self) -> dict[str, dict]:
        if self._profiles is None:
            try:
                self._profiles = json.loads(self._profile_file().read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._profiles = {}
        return self._profiles

    def mod_profile(self, path: str | Path) -> dict[str, int]:
        """
        Quantos textos há por idioma no mod (detecção texto a texto). O resultado fica
        em cache e só é refeito se o arquivo do mod mudar.
        """
        path = Path(path)
        st = path.stat()
        stamp = [st.st_size, int(st.st_mtime)]
        with self._profiles_lock:
            hit = self._load_profiles().get(str(path))
        if hit and hit.get("stamp") == stamp:
            return dict(hit["counts"])

        mod = load(path.read_bytes())
        counts: dict[str, int] = {}
        seen: dict[str, str] = {}
        for u in collect(mod):
            if u.field == "" or not has_letters(u.source):
                continue
            code = seen.get(u.source)
            if code is None:
                code = seen[u.source] = detect_text(u.source)
            counts[code] = counts.get(code, 0) + 1

        with self._profiles_lock:
            profiles = self._load_profiles()
            profiles[str(path)] = {"stamp": stamp, "counts": counts}
            try:
                self._profile_file().parent.mkdir(parents=True, exist_ok=True)
                tmp = self._profile_file().with_suffix(".tmp")
                tmp.write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
                tmp.replace(self._profile_file())
            except OSError:
                pass  # cache é só conveniência
        return counts

    def saved_progress(self, mod_path: str | Path) -> float | None:
        """Progresso (0 a 1) do projeto salvo deste mod no idioma de destino atual; None se não há."""
        p = resolve_project_path(self.projects_folder, mod_path, self.cfg.target_lang)
        if not p.exists():
            return None
        try:
            return Project.load(p).progress()
        except (OSError, ValueError, KeyError):
            return None

    def backup_project(self, mod_path: str | Path) -> Path | None:
        """Cópia de segurança do projeto salvo (pasta 'backup'); guarda as 5 mais recentes."""
        import shutil
        p = resolve_project_path(self.projects_folder, mod_path, self.cfg.target_lang)
        if not p.exists():
            return None
        folder = self.projects_folder / "backup"
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"{p.stem}.{time.strftime('%Y%m%d-%H%M%S')}.bak"
        shutil.copy2(p, dest)
        for old in sorted(folder.glob(f"{p.stem}.*.bak"))[:-5]:
            old.unlink(missing_ok=True)
        return dest

    def reset_progress(self, mod_path: str | Path) -> bool:
        """Apaga o projeto salvo deste mod (volta a 0%), guardando antes uma cópia. Não mexe no mod."""
        p = resolve_project_path(self.projects_folder, mod_path, self.cfg.target_lang)
        if not p.exists():
            return False
        self.backup_project(mod_path)
        p.unlink()
        if self.project is not None and self.mod_path is not None and Path(self.mod_path) == Path(mod_path):
            self.project = None
        return True

    def clean_data(self, keys) -> "CleanResult":
        """Apaga dados do programa (ver cleanup.py). Nunca mexe na pasta do Kenshi."""
        from .cleanup import clean

        def before(key: str) -> None:
            if key == "memoria" and self._memory is not None:
                self._memory.close()
                self._memory = None
            if key == "projetos":
                self.project = None

        res = clean(self.data_folder, keys, before=before)
        if "idiomas" in keys:
            with self._profiles_lock:
                self._profiles = None
        if "glossario" in keys:
            self.reload_glossary()
        return res

    # ------------------------------------------------------------ projeto
    def open_mod(self, path: str | Path) -> Project:
        self.mod_path = Path(path)
        self.undo.clear()  # desfazer vale só para o mod aberto
        self.project = Project.from_mod_file(
            self.mod_path, self.projects_folder,
            target_lang=self.cfg.target_lang, source_lang=self.cfg.source_lang,
            safe_types=self.cfg.safe_record_types,
        )
        self.project.save()
        return self.project

    def detect_project_languages(self) -> dict[str, int]:
        """Detecta o idioma de cada texto do mod aberto (sem traduzir) e guarda no projeto."""
        assert self.project is not None
        return analyze_languages(self.project)

    def set_languages(self, source: str, target: str) -> None:
        """Trocar o idioma de destino abre outro projeto do mesmo mod (cada um guarda o seu)."""
        self.cfg.source_lang, self.cfg.target_lang = source, target
        self.cfg.save()
        if self.mod_path is not None:
            self.open_mod(self.mod_path)

    def visible_units(self, mode: str = "todos", query: str = "", lang: str = "") -> list[tuple[int, Unit]]:
        """Linhas da tabela: (posição na lista do projeto, unidade)."""
        if self.project is None:
            return []
        want = FILTERS.get(mode)
        q = query.strip().casefold()
        out: list[tuple[int, Unit]] = []
        doubt = set(doubtful_indexes(self.project.units)) if mode == "duvidosa" else None
        for i, u in enumerate(self.project.units):
            if doubt is not None and i not in doubt:
                continue
            if want is not None and u.status != want:
                continue
            if lang and u.lang != lang:
                continue
            if q and q not in u.source.casefold() and q not in u.translation.casefold():
                continue
            out.append((i, u))
        return out

    @staticmethod
    def check_translation(unit: Unit, text: str) -> tuple[bool, str]:
        """Confere uma tradução digitada: os marcadores do jogo têm de bater."""
        if not text.strip():
            return True, "vazio: o texto original será mantido"
        if markers_match(unit.source, text):
            n = sum(count_markers(unit.source).values())
            return True, f"{n} marcador(es) do jogo preservado(s)" if n else "ok"
        want, got = count_markers(unit.source), count_markers(text)
        missing = sorted((want - got).elements())
        extra = sorted((got - want).elements())
        parts = []
        if missing:
            parts.append("faltando " + ", ".join(missing))
        if extra:
            parts.append("sobrando " + ", ".join(extra))
        return False, "; ".join(parts)

    def edit(self, index: int, text: str) -> Unit:
        """Grava a edição manual (vira 'revisada') e aprende na memória de tradução."""
        assert self.project is not None
        unit = self.project.units[index]
        ok, msg = self.check_translation(unit, text)
        if not ok:
            raise ValueError(f"Marcadores do jogo diferentes do original ({msg}).")
        self.undo.push(unit)
        self.project.set_translation(unit.key, text)
        if text.strip():
            self.memory.put(unit.source, self.project.target_lang, text, origin="revisao")
        self.project.save()
        return unit

    def undo_edit(self) -> int | None:
        """Desfaz a última edição manual. Devolve a posição do texto afetado (None: nada a desfazer).
        A memória de tradução guarda o que foi digitado antes; ela não é apagada."""
        if self.project is None:
            return None
        idx = self.undo.pop(self.project.units)
        if idx is not None:
            self.project.save()
        return idx

    def doubtful(self) -> Doubtful:
        return count_doubtful(self.project.units) if self.project else Doubtful()

    def source_language_counts(self) -> dict[str, int]:
        return source_languages(self.project.units) if self.project else {}

    # ------------------------------------------------------------ traduzir
    def make_provider(self) -> Provider:
        c = self.cfg
        return make_provider(c.provider, c.api_key, c.server_url, c.free_order, c.services, c.use_free, c.spread)

    def options(self, retranslate: bool = False) -> Options:
        c = self.cfg
        return Options(
            workers=max(1, int(c.workers)),
            retranslate=retranslate,
            keep_character_names=c.keep_character_names,
            multi_source=c.multi_source,
            source_langs=tuple(c.source_langs) if c.multi_source else (),
            notify_switch=c.notify_switch,
            on_message=getattr(self, "on_message", None),
        )

    def translate(
        self,
        provider: Provider,
        progress: ProgressFn | None = None,
        cancel: threading.Event | None = None,
        retranslate: bool = False,
    ) -> Report:
        assert self.project is not None
        return translate_project(
            self.project, provider, glossary=self.glossary, memory=self.memory,
            options=self.options(retranslate), progress=progress, cancel=cancel,
        )

    def translate_many(
        self,
        paths: list[Path],
        provider: Provider,
        progress=None,
        cancel: threading.Event | None = None,
        retranslate: bool = False,
        install: bool = False,
    ) -> list[ManyResult]:
        """
        Traduz uma fila de mods, um depois do outro (cada um com a tradução em
        paralelo por dentro), gera o mod de tradução de cada um e, se pedido, instala.
        progress(i, n, nome, feitos, total, mensagem).
        """
        cancel = cancel or threading.Event()
        results: list[ManyResult] = []
        n = len(paths)
        for i, path in enumerate(paths):
            if cancel.is_set():
                break
            path = Path(path)
            res = ManyResult(name=path.name)
            results.append(res)
            try:
                proj = Project.from_mod_file(
                    path, self.projects_folder,
                    target_lang=self.cfg.target_lang, source_lang=self.cfg.source_lang,
                    safe_types=self.cfg.safe_record_types,
                )
                proj.save()
                res.report = translate_project(
                    proj, provider, glossary=self.glossary, memory=self.memory,
                    options=self.options(retranslate),
                    progress=(lambda d, t, m, i=i, name=path.name: progress(i, n, name, d, t, m)) if progress else None,
                    cancel=cancel,
                )
                if any(u.translation.strip() for u in proj.units):
                    res.built = build_translation(proj, path, self.default_output_folder, mode=self.cfg.translation_mode)
                    if install and not res.built.problems:
                        dirs = self.locate_game()
                        if dirs.kenshi is None:
                            res.error = "mod gerado, mas não achei a pasta do Kenshi para instalar"
                        else:
                            res.installed = install_translation_info(dirs.kenshi, res.built.path, proj.mod_name,
                                                                    Path(path).parent if self.cfg.copy_images else None,
                                                                    self._text_files(proj.mod_name, dirs, cancel)).dest
                            self._install_locale(proj.mod_name, dirs, cancel)
            except ProviderBroken as e:
                res.error = str(e)
                break  # o serviço está instável: não adianta seguir para os próximos
            except Exception as e:  # noqa: BLE001 - um mod ruim não derruba a fila
                res.error = f"{type(e).__name__}: {e}"
        return results

    # ------------------------------------------------------------ gerar / instalar
    @property
    def default_output_folder(self) -> Path:
        """Onde o mod de tradução é gerado. Nunca na pasta do Workshop, que o Steam gerencia."""
        return self.data_folder / "mods_traduzidos"

    def build(self, out_dir: str | Path | None = None) -> BuildResult:
        assert self.project is not None and self.mod_path is not None
        out = Path(out_dir) if out_dir else self.default_output_folder
        return build_translation(self.project, self.mod_path, out, mode=self.cfg.translation_mode)

    def install(self, built: str | Path) -> tuple[Path, bool]:
        """Instala o mod traduzido. Os detalhes (onde ficou o backup do original) ficam em last_install."""
        assert self.project is not None
        dirs = self.locate_game()
        if dirs.kenshi is None:
            raise FileNotFoundError("Pasta do Kenshi não encontrada.")
        src = self._original_dir(self.project.mod_name, dirs) if self.cfg.copy_images else None
        self.last_install = install_translation_info(dirs.kenshi, built, self.project.mod_name, src,
                                                     self._text_files(self.project.mod_name, dirs))
        self._install_locale(self.project.mod_name, dirs)
        return self.last_install.dest, self.last_install.cfg_changed

    def has_original_backup(self) -> bool:
        """True se existe Kenshi/mods/<nome>/<nome>.mod.original deste mod (dá para restaurar)."""
        if self.project is None:
            return False
        dirs = self.locate_game()
        return dirs.kenshi is not None and has_backup(dirs.kenshi, self.project.mod_name)

    def restore_original(self) -> RestoreResult:
        """Desfaz a instalação: o .mod original volta; a tradução instalada fica como .mod.traduzido."""
        assert self.project is not None
        dirs = self.locate_game()
        if dirs.kenshi is None:
            raise FileNotFoundError("Pasta do Kenshi não encontrada.")
        return restore_original(dirs.kenshi, self.project.mod_name)

    # ------------------------------------------------------------ segunda passada
    def second_pass(
        self,
        service: str | None = None,
        progress: ProgressFn | None = None,
        cancel: threading.Event | None = None,
    ) -> Report:
        """
        Refaz só os textos em "Conferir", com outro serviço (`service` = chave de providers.SPECS;
        None usa o serviço atual). Não usa a memória de tradução (ela pode ter o mesmo erro) e não
        troca uma tradução parcial por nada: se o novo resultado também não presta, fica como estava.
        """
        assert self.project is not None
        c = self.cfg
        provider = (make_provider(service, c.api_key, c.server_url, c.free_order, c.services, c.use_free, c.spread)
                    if service else self.make_provider())
        opts = self.options()
        opts.only_attention = True
        self.project.save()
        return translate_project(self.project, provider, glossary=self.glossary, memory=None,
                                 options=opts, progress=progress, cancel=cancel)

    def _text_files(self, mod_name: str, dirs: KenshiDirs, cancel=None) -> dict[str, bytes]:
        """
        Arquivos da pasta do mod que são traduzidos ao instalar: .txt de frases (ex.: tips.txt) e
        arquivos de idioma .mo (juntados ao idioma do jogo), cada um se a sua opção estiver ligada.
        Devolve {caminho relativo à pasta do mod: conteúdo}. Qualquer falha em um item só o deixa
        como está (copiado do original); nunca impede a instalação.
        """
        out: dict[str, bytes] = {}
        if not self.cfg.translate_text_files:
            return out
        try:
            folder = next((e.path.parent for e in scan_mods(dirs) if e.name == mod_name), None)
        except Exception:  # noqa: BLE001
            return out
        if folder is None:
            return out
        provider = None
        if self.cfg.translate_text_files:
            try:
                files = find_text_files(folder)
                if files:
                    provider = self.make_provider()
                    out.update(translate_text_files(files, provider, self.cfg.target_lang, self.cfg.source_lang,
                                                    self.glossary, self.memory, cancel))
            except Exception:  # noqa: BLE001
                pass
        return out

    def _install_locale(self, mod_name: str, dirs: KenshiDirs, cancel=None) -> int:
        """
        Opção do .mo: troca a pasta `locale` do mod instalado pelo pacote de idioma do jogo com as
        frases do mod traduzidas. A `locale` do mod fica guardada como `locale_off`.
        Devolve quantos arquivos escreveu (0 = nada mudou). Falhas deixam tudo como estava.
        """
        import shutil

        self.last_locale_files = 0
        if not self.cfg.translate_locale_files or dirs.kenshi is None:
            return 0
        dest = Path(dirs.kenshi) / "mods" / Path(mod_name).stem
        try:
            if not (dest / "locale").is_dir():
                return 0
            src = "en" if self.cfg.source_lang in ("", "auto") else self.cfg.source_lang
            files = build_locale_pack(dest, dirs.kenshi, self.make_provider(), self.cfg.target_lang, src,
                                      self.glossary, self.memory, cancel)
            if not files:
                return 0
            loc, off = dest / "locale", dest / "locale_off"
            if off.exists():  # a original já está guardada: a atual é uma cópia nova ou de uma instalação anterior
                shutil.rmtree(loc)
            else:
                loc.rename(off)
            for rel, data in files.items():
                t = dest / rel
                t.parent.mkdir(parents=True, exist_ok=True)
                t.write_bytes(data)
            self.last_locale_files = len(files)
            return len(files)
        except Exception:  # noqa: BLE001 - nunca impede a instalação
            return 0

    def _original_dir(self, mod_name: str, dirs: KenshiDirs) -> Path | None:
        """Pasta do mod original (Workshop ou pasta do jogo): de lá vem a imagem/ícone."""
        for e in scan_mods(dirs):
            if e.name == mod_name and any(f.suffix.lower() in IMAGE_EXTS for f in e.path.parent.iterdir()):
                return e.path.parent
        return None

    def copy_to_game(self, entries: list[ModEntry]) -> list[tuple[str, str]]:
        """Copia mods do Workshop para a pasta do jogo. Devolve [(nome, resultado em português)]."""
        dirs = self.locate_game()
        if dirs.kenshi is None:
            raise FileNotFoundError("Pasta do Kenshi não encontrada.")
        out: list[tuple[str, str]] = []
        for e in entries:
            if e.source != "workshop":
                out.append((e.name, "não é do Workshop (já está na pasta do jogo ou é arquivo avulso)"))
                continue
            try:
                dest, n = copy_mod_to_game(e.path, dirs.kenshi)
                out.append((e.name, f"{n} arquivo(s) copiado(s) para {dest}"))
            except (OSError, ValueError) as ex:
                out.append((e.name, f"falhou: {ex}"))
        return out
