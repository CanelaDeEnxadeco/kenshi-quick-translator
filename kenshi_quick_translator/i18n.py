"""
Idioma da INTERFACE do programa (não do mod): Português (padrão), English e Español.

O programa foi escrito em português; aqui há uma tabela português → inglês/espanhol.
`apply(raiz)` troca os textos dos botões, rótulos e abas já criados, e as caixas de
mensagem e o texto das variáveis passam por `tr()`. Textos montados com números
(ex.: "12 textos pendentes") são traduzidos por pedaços. O que não está na tabela
fica em português: avise para eu completar.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

LANG_NAMES = {"pt": "Português (Brasil)", "en": "English", "es": "Español", "ru": "Русский", "zh": "中文"}
_lang = "pt"

# (português, inglês, espanhol). Textos curtos só valem como texto inteiro; os longos também como pedaço.
ROWS: list[tuple[str, str, str]] = [
    ("Zerar tradução deste mod", "Reset this mod's translation", "Reiniciar traducción de este mod"),
    ("Abrir pasta dos projetos", "Open projects folder", "Abrir carpeta de proyectos"),
    ("Zerar tradução", "Reset translation", "Reiniciar traducción"),
    ("Resumo da tradução", "Translation summary", "Resumen de la traducción"),
    ("Traduzidos:", "Translated:", "Traducidos:"), ("Da memória:", "From memory:", "De la memoria:"),
    ("Para conferir:", "To review:", "Para revisar:"), ("Ignorados:", "Ignored:", "Ignorados:"),
    ("Com falha:", "Failed:", "Con fallo:"), ("Tempo:", "Time:", "Tiempo:"),
    ("Escolha na lista o mod que quer zerar.", "Pick the mod to reset from the list.", "Elige en la lista el mod que quieres reiniciar."),
    ("Nenhum desses mods tinha progresso salvo.", "None of these mods had saved progress.", "Ninguno de estos mods tenía progreso guardado."),
    ("Pasta dos projetos", "Projects folder", "Carpeta de proyectos"),
    ("traduza mods rapidamente", "translate mods quickly", "traduce mods rápidamente"),
    ("?  Ajuda", "?  Help", "?  Ayuda"), ("Como usar", "How to use", "Cómo usar"),
    ("⚙  Configurações", "⚙  Settings", "⚙  Configuración"),
    ("Seus mods", "Your mods", "Tus mods"), ("Buscar:", "Search:", "Buscar:"),
    ("Mod", "Mod", "Mod"), ("Idioma", "Language", "Idioma"), ("Feito", "Done", "Hecho"), ("Onde", "Where", "Dónde"),
    ("Não achei o Kenshi sozinho. Clique em “Pasta do Kenshi…” ou use “Abrir arquivo…”.", "I could not find Kenshi by myself. Click “Kenshi folder…” or use “Open file…”.", "No encontré Kenshi solo. Haz clic en “Carpeta de Kenshi…” o usa “Abrir archivo…”."),
    ("⟳ Atualizar", "⟳ Refresh", "⟳ Actualizar"), ("Abrir arquivo…", "Open file…", "Abrir archivo…"),
    ("Pasta do Kenshi…", "Kenshi folder…", "Carpeta de Kenshi…"),
    ("Copiar mod para a pasta do jogo", "Copy mod to the game folder", "Copiar mod a la carpeta del juego"),
    ("Dica: Ctrl+clique escolhe vários mods para traduzir em fila.", "Tip: Ctrl+click selects several mods to translate in a queue.", "Consejo: Ctrl+clic elige varios mods para traducir en cola."),
    ("Mod escolhido", "Selected mod", "Mod elegido"), ("Nenhum mod aberto", "No mod open", "Ningún mod abierto"),
    ("Clique em um mod na lista da esquerda para começar.", "Click a mod in the list on the left to start.", "Haz clic en un mod de la lista de la izquierda para empezar."),
    ("Como traduzir", "How to translate", "Cómo traducir"),
    ("Idioma do mod:", "Mod language:", "Idioma del mod:"), ("Traduzir para:", "Translate to:", "Traducir a:"),
    ("Este mod tem mais de um idioma (ex.: inglês e chinês)", "This mod has more than one language (e.g. English and Chinese)", "Este mod tiene más de un idioma (ej.: inglés y chino)"),
    ("Idiomas que o mod tem (cada texto é identificado sozinho):", "Languages in the mod (each text is detected on its own):", "Idiomas del mod (cada texto se detecta solo):"),
    ("Não traduzir nomes de personagens", "Do not translate character names", "No traducir nombres de personajes"),
    ("Serviço:", "Service:", "Servicio:"), ("Chave:", "Key:", "Clave:"), ("Servidor:", "Server:", "Servidor:"),
    ("Mais de uma chave? Separe com ;  (divide o trabalho entre elas)", "More than one key? Separate with ;  (work is split among them)", "¿Más de una clave? Sepáralas con ;  (el trabajo se reparte entre ellas)"),
    ("Testar serviço", "Test service", "Probar servicio"), ("Velocidade:", "Speed:", "Velocidad:"),
    ("Cada parte é um pedido ao serviço. Mais partes = mais rápido, até o limite do serviço. Se ele reclamar, o programa diminui sozinho.", "Each part is one request to the service. More parts = faster, up to the service limit. If it complains, the program slows down by itself.", "Cada parte es una petición al servicio. Más partes = más rápido, hasta el límite del servicio. Si se queja, el programa reduce solo."),
    ("Serviços gratuitos limitam os pedidos: o programa já espaça e troca de serviço sozinho. Use 2 ou 3 partes.", "Free services limit requests: the program already spaces them out and switches service by itself. Use 2 or 3 parts.", "Los servicios gratuitos limitan las peticiones: el programa ya las espacia y cambia de servicio solo. Usa 2 o 3 partes."),
    ("▶  Traduzir este mod", "▶  Translate this mod", "▶  Traducir este mod"), ("▶▶  Traduzir selecionados", "▶▶  Translate selected", "▶▶  Traducir seleccionados"),
    ("■  Parar", "■  Stop", "■  Detener"), ("Refazer automáticas", "Redo automatic ones", "Rehacer automáticas"),
    ("Instalar no jogo ao terminar (fila)", "Install in the game when done (queue)", "Instalar en el juego al terminar (cola)"),
    ("Escolha um mod na lista para começar.", "Pick a mod from the list to start.", "Elige un mod de la lista para empezar."),
    ("Revise e gere o mod", "Review and build the mod", "Revisa y genera el mod"), ("Mostrar:", "Show:", "Mostrar:"),
    ("Estado", "Status", "Estado"), ("Original", "Original", "Original"), ("Tradução", "Translation", "Traducción"),
    ("Tradução (edite aqui)", "Translation (edit here)", "Traducción (edita aquí)"),
    ("Aplicar e próximo (Ctrl+Enter)", "Apply and next (Ctrl+Enter)", "Aplicar y siguiente (Ctrl+Enter)"),
    ("Copiar original", "Copy original", "Copiar original"),
    ("Gerar mod de tradução…", "Build translation mod…", "Generar mod de traducción…"),
    ("Instalar no jogo", "Install in game", "Instalar en el juego"), ("Glossário…", "Glossary…", "Glosario…"),
    ("Exportar PO…", "Export PO…", "Exportar PO…"), ("Importar PO…", "Import PO…", "Importar PO…"),
    ("Trocar o idioma de destino abre outro projeto do mesmo mod (cada um guarda o seu).", "Changing the target language opens another project of the same mod (each keeps its own).", "Cambiar el idioma de destino abre otro proyecto del mismo mod (cada uno guarda el suyo)."),
    ("Lê a pasta do jogo e mostra os mods; idioma e progresso chegam em segundo plano.", "Reads the game folder and lists the mods; language and progress arrive in the background.", "Lee la carpeta del juego y muestra los mods; idioma y progreso llegan en segundo plano."),
    ("Um mod escolhido abre; vários escolhidos (Ctrl+clique) viram uma fila.", "One selected mod opens; several (Ctrl+click) become a queue.", "Un mod elegido se abre; varios (Ctrl+clic) forman una cola."),
    ("Escolha o mod", "Choose the mod", "Elige el mod"), ("Mods do Kenshi", "Kenshi mods", "Mods de Kenshi"),
    ("Pasta onde o Kenshi está instalado", "Folder where Kenshi is installed", "Carpeta donde está instalado Kenshi"),
    ("Essa pasta não parece ser a do Kenshi (falta a pasta 'data').", "That folder does not look like Kenshi's (no 'data' folder).", "Esa carpeta no parece la de Kenshi (falta la carpeta 'data')."),
    ("Aguarde", "Wait", "Espera"), ("Espere a tarefa terminar ou clique em Parar.", "Wait for the task to finish or click Stop.", "Espera a que termine la tarea o haz clic en Detener."),
    ("Marcadores do jogo", "Game markers", "Marcadores del juego"), ("Serviço", "Service", "Servicio"),
    ("Testando o serviço…", "Testing the service…", "Probando el servicio…"), ("Refazer", "Redo", "Rehacer"),
    ("Refazer as traduções automáticas e as marcadas para conferir?\nO que você já revisou NÃO é alterado.", "Redo the automatic translations and those marked for review?\nWhat you already reviewed is NOT changed.", "¿Rehacer las traducciones automáticas y las marcadas para revisar?\nLo que ya revisaste NO se modifica."),
    ("Idiomas", "Languages", "Idiomas"),
    ("Marque pelo menos um idioma que o mod tem, ou desmarque a opção de vários idiomas.", "Tick at least one language the mod has, or untick the multi-language option.", "Marca al menos un idioma del mod, o desmarca la opción de varios idiomas."),
    ("Começando…", "Starting…", "Empezando…"), ("Kenshi Quick Translator", "Kenshi Translator", "Traductor de Kenshi"),
    ("Escolha um mod na lista primeiro.", "Pick a mod from the list first.", "Elige primero un mod de la lista."),
    ("Escolha um ou mais mods na lista (Ctrl+clique para vários).", "Pick one or more mods in the list (Ctrl+click for several).", "Elige uno o más mods de la lista (Ctrl+clic para varios)."),
    ("Traduzir em fila", "Translate in a queue", "Traducir en cola"),
    ("Parando… o que já foi traduzido fica salvo.", "Stopping… what was already translated is saved.", "Deteniendo… lo ya traducido queda guardado."),
    ("Não consegui ler esse mod.", "I could not read that mod.", "No pude leer ese mod."), ("Não consegui ler o mod", "Could not read the mod", "No pude leer el mod"),
    ("Serviço instável: parei.", "Unstable service: I stopped.", "Servicio inestable: me detuve."), ("O serviço falhou", "The service failed", "El servicio falló"),
    ("Erro.", "Error.", "Error."), ("Erro inesperado", "Unexpected error", "Error inesperado"), ("Serviço ok.", "Service OK.", "Servicio OK."),
    ("O serviço não respondeu.", "The service did not answer.", "El servicio no respondió."),
    ("Avisos do serviço", "Service notices", "Avisos del servicio"),
    ("Fila terminada", "Queue finished", "Cola terminada"), ("Nada para gerar", "Nothing to build", "Nada que generar"),
    ("Ainda não há nenhuma tradução. Clique em “Traduzir este mod”.", "There is no translation yet. Click “Translate this mod”.", "Aún no hay ninguna traducción. Haz clic en “Traducir este mod”."),
    ("Onde salvar o mod de tradução?", "Where to save the translation mod?", "¿Dónde guardar el mod de traducción?"),
    ("Não consegui gerar o mod", "Could not build the mod", "No pude generar el mod"), ("Gerado, mas confira", "Built, but please check", "Generado, pero revisa"),
    ("Mod gerado", "Mod built", "Mod generado"),
    ("Escolha na lista os mods do Workshop que quer copiar.", "Pick in the list the Workshop mods you want to copy.", "Elige en la lista los mods del Workshop que quieres copiar."),
    ("Copiar para a pasta do jogo", "Copy to the game folder", "Copiar a la carpeta del juego"), ("Copiar mod", "Copy mod", "Copiar mod"),
    ("Nada para instalar", "Nothing to install", "Nada que instalar"), ("Ainda não há nenhuma tradução.", "There is no translation yet.", "Aún no hay ninguna traducción."),
    ("Pasta do Kenshi", "Kenshi folder", "Carpeta de Kenshi"), ("Não achei a pasta do Kenshi.", "I could not find the Kenshi folder.", "No encontré la carpeta de Kenshi."),
    ("Não consegui instalar", "Could not install", "No pude instalar"), ("Instalado", "Installed", "Instalado"),
    ("mods.cfg atualizado.", "mods.cfg updated.", "mods.cfg actualizado."), ("mods.cfg já tinha o mod.", "mods.cfg already had the mod.", "mods.cfg ya tenía el mod."),
    ("Instalado. Abra o Kenshi para testar.", "Installed. Open Kenshi to test.", "Instalado. Abre Kenshi para probar."),
    ("Glossário", "Glossary", "Glosario"), ("Termo no mod", "Term in the mod", "Término en el mod"), ("Como deve ficar", "How it should read", "Cómo debe quedar"),
    ("Termo:", "Term:", "Término:"), ("Tradução:", "Translation:", "Traducción:"),
    ("Adicionar / atualizar", "Add / update", "Añadir / actualizar"), ("Remover", "Remove", "Quitar"), ("Fechar", "Close", "Cerrar"),
    ("Termos que devem sair sempre do mesmo jeito. Deixe a tradução vazia para NÃO traduzir o termo (bom para nomes de lugares e facções).", "Terms that must always come out the same way. Leave the translation empty to NOT translate the term (good for place and faction names).", "Términos que deben salir siempre igual. Deja la traducción vacía para NO traducir el término (bueno para nombres de lugares y facciones)."),
    # pedaços de textos montados com números
    (" textos pendentes. Clique em “Traduzir este mod”.", " texts pending. Click “Translate this mod”.", " textos pendientes. Haz clic en “Traducir este mod”."),
    (" textos para traduzir", " texts to translate", " textos por traducir"),
    (" textos/min · faltam ≈ ", " texts/min · remaining ≈ ", " textos/min · faltan ≈ "),
    (" pendentes | ", " pending | ", " pendientes | "), (" automáticos | ", " automatic | ", " automáticos | "),
    (" p/ conferir | ", " to review | ", " p/ revisar | "), (" revisados | ", " reviewed | ", " revisados | "),
    (" resolvido", " resolved", " resuelto"), (" traduzidos", " translated", " traducidos"),
    (" da memória", " from memory", " de la memoria"), (" para conferir", " to review", " para revisar"),
    (" com falha", " failed", " con fallo"), ("Interrompido. ", "Interrupted. ", "Interrumpido. "), ("Pronto. ", "Done. ", "Listo. "),
    ("Fila terminada: ", "Queue finished: ", "Cola terminada: "), (" (instalado)", " (installed)", " (instalado)"),
    ("Lendo ", "Reading ", "Leyendo "), ("Gerado: ", "Built: ", "Generado: "), ("PO salvo: ", "PO saved: ", "PO guardado: "),
    (" traduções importadas (marcadas como revisadas).", " translations imported (marked as reviewed).", " traducciones importadas (marcadas como revisadas)."),
    (". Deixei marcada a opção de vários idiomas.", ". I ticked the multi-language option.", ". Dejé marcada la opción de varios idiomas."),
    (". ATENÇÃO: este mod tem mais de um idioma: ", ". WARNING: this mod has more than one language: ", ". ATENCIÓN: este mod tiene más de un idioma: "),
    (" parte(s) ao mesmo tempo", " part(s) at the same time", " parte(s) a la vez"), (" ao mesmo tempo", " at the same time", " a la vez"),
    (" mod(s) do Workshop para a pasta mods do Kenshi?\nO Workshop não é alterado; arquivos iguais na pasta do jogo serão substituídos.", " Workshop mod(s) to Kenshi's mods folder?\nThe Workshop is not changed; identical files in the game folder will be replaced.", " mod(s) del Workshop a la carpeta mods de Kenshi?\nEl Workshop no se modifica; los archivos iguales en la carpeta del juego se reemplazarán."),
    ("Isto vai:\n• copiar o mod de tradução para ", "This will:\n• copy the translation mod to ", "Esto va a:\n• copiar el mod de traducción a "),
    ("\n• acrescentar uma linha em data/mods.cfg, logo depois de “", "\n• add a line to data/mods.cfg, right after “", "\n• añadir una línea en data/mods.cfg, justo después de “"),
    ("” (é feito um backup do mods.cfg antes).\n\nContinuar?", "” (mods.cfg is backed up first).\n\nContinue?", "” (antes se hace una copia de mods.cfg).\n\n¿Continuar?"),
    ("\n\nAtenção, a conferência achou:\n- ", "\n\nWarning, the check found:\n- ", "\n\nAtención, la revisión encontró:\n- "),
    ("\n\nProblemas encontrados:\n- ", "\n\nProblems found:\n- ", "\n\nProblemas encontrados:\n- "),
    (" textos traduzidos. Conferência do arquivo: ok.\nO mod original não foi alterado.", " texts translated. File check: OK.\nThe original mod was not changed.", " textos traducidos. Revisión del archivo: ok.\nEl mod original no se modificó."),
    ("\n\nOs mods de tradução estão em:\n", "\n\nThe translation mods are in:\n", "\n\nLos mods de traducción están en:\n"), ("\n\nAbrir essa pasta?", "\n\nOpen that folder?", "\n\n¿Abrir esa carpeta?"),
    (" mods, um depois do outro?\n\nPara cada um será gerado o mod de tradução", " mods, one after the other?\n\nFor each one the translation mod will be built", " mods, uno tras otro?\n\nPara cada uno se generará el mod de traducción"),
    (" e instalado no jogo", " and installed in the game", " e instalado en el juego"),
    # avisos do agregado
    (" bloqueou (muitos pedidos)", " blocked us (too many requests)", " nos bloqueó (demasiadas peticiones)"),
    (" recusou o acesso", " refused access", " rechazó el acceso"), (" não respondeu", " did not answer", " no respondió"),
    (". Fica de fora por ", ". Left out for ", ". Queda fuera por "), (" Passei para o ", " Switched to ", " Cambié a "),
    (" Sem outro serviço livre agora; vou esperar.", " No other service free right now; I will wait.", " Ningún otro servicio libre ahora; voy a esperar."),
    ("Todos os serviços estão ocupados. Espero ", "All services are busy. Waiting ", "Todos los servicios están ocupados. Espero "),
    (" e tento de novo.", " and trying again.", " y vuelvo a intentar."),
    ("Todos os serviços falharam: ", "All services failed: ", "Todos los servicios fallaron: "),
    # janela de configurações
    ("Configurações gerais", "General settings", "Configuración general"),
    ("Idioma do programa:", "Program language:", "Idioma del programa:"),
    ("Avisar quando o programa trocar de serviço", "Warn when the program switches service", "Avisar cuando el programa cambie de servicio"),
    ("Copiar a imagem/ícone do mod original ao instalar", "Copy the original mod's image/icon when installing", "Copiar la imagen/icono del mod original al instalar"),
    ("Tema:", "Theme:", "Tema:"), ("Claro", "Light", "Claro"), ("Escuro", "Dark", "Oscuro"),
    ("Seguir o Windows", "Follow Windows", "Seguir Windows"),
    ("Salvar", "Save", "Guardar"), ("Cancelar", "Cancel", "Cancelar"),
    ("Esta é a língua dos menus e botões; não muda o idioma da tradução do mod.", "This is the language of menus and buttons; it does not change the mod translation language.", "Es el idioma de menús y botones; no cambia el idioma de la traducción del mod."),
    ("Salvo. Alguns textos só mudam ao reiniciar o programa.", "Saved. Some texts only change after restarting the program.", "Guardado. Algunos textos solo cambian al reiniciar el programa."),
]

HELP = {
    "en": ("How to use, in 3 steps:\n\n1. Click a mod in the list on the left (or “Open file…”).\n    Ctrl+click selects several mods to translate in a queue.\n\n"
           "2. Choose the target language and the translation service, then click “Translate”.\n    If the mod has more than one language (e.g. English and Chinese), tick\n    “This mod has more than one language”. The program already suggests it.\n\n"
           "3. Check the yellow lines (“Review”), fix what you like in the box on the right\n    and click “Build translation mod” or “Install in game”.\n\n"
           "The original mod file is not changed when building; when installing, the original is kept as a backup. Your work is saved: you can close and continue later."),
    "es": ("Cómo usar, en 3 pasos:\n\n1. Haz clic en un mod de la lista de la izquierda (o en “Abrir archivo…”).\n    Ctrl+clic elige varios mods para traducir en cola.\n\n"
           "2. Elige el idioma de destino y el servicio de traducción y haz clic en “Traducir”.\n    Si el mod tiene más de un idioma (por ejemplo inglés y chino), marca\n    “Este mod tiene más de un idioma”. El programa ya lo sugiere solo.\n\n"
           "3. Revisa las líneas amarillas (“Revisar”), corrige lo que quieras en el cuadro de la derecha\n    y haz clic en “Generar mod de traducción” o “Instalar en el juego”.\n\n"
           "El archivo del mod original no se modifica al generar; al instalar, el original se guarda como copia de seguridad. El trabajo queda guardado: puedes cerrar y continuar después."),
}

_RE_IN = re.compile(r" em (?=\d+ ?(?:s|min|h)\b)")  # "… em 3 s"
_exact: dict[str, str] = {}
_frags: list[tuple[str, str]] = []
_pats: list = []


def _build() -> None:
    _exact.clear()
    _frags.clear()
    _pats.clear()
    from .i18n_more import EXACT_ONLY, MORE, PATTERNS

    if _lang in ("ru", "zh"):
        from .i18n_extra import RU_ZH

        k = 0 if _lang == "ru" else 1
        pairs = [(row[0], RU_ZH[n][k]) for n, row in enumerate(ROWS) if n < len(RU_ZH)]
        mcol = 3 if _lang == "ru" else 4
    else:
        col = {"en": 1, "es": 2}.get(_lang)
        if col is None:
            return
        pairs = [(row[0], row[col]) for row in ROWS]
        mcol = col
    for pt_text, other in pairs:
        _exact[pt_text] = other
        if len(pt_text) >= 9 or pt_text.endswith((". ", ": ", " ")):
            _frags.append((pt_text, other))
    for n, row in enumerate(MORE):
        _exact[row[0]] = row[mcol]
        if n >= EXACT_ONLY and (len(row[0]) >= 9 or row[0].endswith((". ", ": ", " "))):
            _frags.append((row[0], row[mcol]))
    _pats.extend((re.compile(p[0]), p[mcol]) for p in PATTERNS)
    _frags.sort(key=lambda p: -len(p[0]))


def set_language(code: str) -> None:
    global _lang
    _lang = code if code in LANG_NAMES else "pt"
    _build()


def language() -> str:
    return _lang


def tr(text):
    """Traduz um texto da interface. Fora do português, troca o que reconhece; o resto fica igual."""
    if _lang == "pt" or not isinstance(text, str) or not text:
        return text
    hit = _exact.get(text)
    if hit is not None:
        return hit
    out = text
    for pt, other in _frags:
        if pt in out:
            out = out.replace(pt, other)
    out = _RE_IN.sub({"en": " in ", "es": " en ", "ru": " за ", "zh": " 用时 "}[_lang], out)
    for rx, repl in _pats:
        out = rx.sub(repl, out)
    return out


_NOMES = ("Inglês", "Chinês", "Japonês", "Coreano", "Russo", "Ucraniano", "Espanhol", "Francês", "Alemão",
          "Italiano", "Português", "Polonês", "Turco", "Indefinido", "indefinido")


def names(text):
    """Traduz nomes de idiomas dentro de um texto (ex.: 'Inglês + Japonês')."""
    if _lang == "pt" or not isinstance(text, str):
        return text
    for n in _NOMES:
        if n in text:
            text = text.replace(n, _exact.get(n, n))
    return text


def help_text(pt_text: str) -> str:
    if _lang in ("ru", "zh"):
        from .i18n_extra import HELP_RU_ZH

        return HELP_RU_ZH[_lang]
    return HELP.get(_lang, pt_text)


# ---------------------------------------------------------------- aplicar na janela
def _walk(w):
    yield w
    for c in w.winfo_children():
        yield from _walk(c)


def apply(root) -> None:
    """Troca os textos dos widgets já criados. Guarda o original para poder voltar ao português."""
    for w in _walk(root):
        try:
            if isinstance(w, ttk.Notebook):
                for i in range(w.index("end")):
                    key = f"_i18n_tab{i}"
                    orig = getattr(w, key, None) or w.tab(i, "text")
                    setattr(w, key, orig)
                    w.tab(i, text=tr(orig))
                continue
            if isinstance(w, ttk.Treeview):
                heads = getattr(w, "_i18n_heads", None)
                if heads is None:
                    heads = {c: w.heading(c, "text") for c in w["columns"]}
                    w._i18n_heads = heads
                for c, orig in heads.items():
                    w.heading(c, text=tr(orig))
                continue
            if "text" in w.keys() and not isinstance(w, tk.Text):
                if str(w.cget("textvariable") if "textvariable" in w.keys() else ""):
                    continue  # textos de variável são traduzidos quando a variável muda
                orig = getattr(w, "_i18n_text", None)
                if orig is None:
                    orig = str(w.cget("text"))
                    w._i18n_text = orig
                if orig:
                    w.configure(text=tr(orig))
        except tk.TclError:
            pass


_patched = False


def install_hooks() -> None:
    """Faz caixas de mensagem, seletores de pasta e variáveis de texto passarem por tr()."""
    global _patched
    if _patched:
        return
    _patched = True
    for name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askretrycancel", "askquestion"):
        orig = getattr(messagebox, name)

        def wrap(title=None, message=None, _orig=orig, **kw):
            return _orig(tr(title), tr(message), **kw)

        setattr(messagebox, name, wrap)
    for name in ("askdirectory", "askopenfilename", "asksaveasfilename", "askopenfilenames"):
        orig = getattr(filedialog, name)

        def wrap_fd(*a, _orig=orig, **kw):
            if "title" in kw:
                kw["title"] = tr(kw["title"])
            return _orig(*a, **kw)

        setattr(filedialog, name, wrap_fd)
    orig_set = tk.StringVar.set

    def var_set(self, value):
        return orig_set(self, tr(value))

    tk.StringVar.set = var_set  # type: ignore[method-assign]
