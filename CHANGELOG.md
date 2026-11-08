# Changelog

## 0.7.6
- Mod list buttons: the three least used ("Abrir pasta do mod", "Abrir pasta dos projetos", "Zerar tradução deste mod") moved into a "Mais ações" menu; the side bar now has 4 buttons (Atualizar, Abrir arquivo, Pasta do Kenshi, Mais ações) plus "Copiar mod para a pasta do jogo". The menu is built when opened, so it follows the interface language. Tutorial text and tooltip updated.
- Buttons: a thin outline in the theme's line colour (flat look; highlighted buttons keep their own colour and a disabled one fades fully), and small icons on some buttons (+ Abrir arquivo, ⌂ Pasta do Kenshi, → Copiar mod, ⬇ Instalar, ↶ Restaurar, ✓ Aplicar). The translator now keeps a leading icon and translates the rest. Rounded corners and shadows are NOT done: the Tk themed buttons cannot draw them without images, which would be risky with Windows screen scaling.
- Service box: shorter names ("Agregado (recomendado)", "Simulado (só para testar)") so they are no longer cut off; the box is a little narrower.
- Tests updated for the menu (`test_tutorial`, `test_tips_buttons`). Seen only in screenshots on Tk 9 under Linux; the icons use symbols that Windows fonts may draw differently, not checked on Windows.
- Step 2 ("Como traduzir") is cleaner: the less used options moved into a collapsible "Opções avançadas" block (closed by default): more than one language, do not translate character names, install when done (queue) and speed. Next to the button a one-line summary shows what is on (e.g. "velocidade 3 · nomes preservados"). The block opens by itself when you tick "more than one language" and when the tutorial explains a part inside it. "Testar serviço" now sits next to the service box, and step 1 is one line. Result: the review card (step 3) starts about 50 px higher, so more of it shows without scrolling. The state of the block is not saved between runs. New texts translated to en/es/ru/zh (not reviewed by native speakers). Seen in screenshots on Tk 9 under Linux (Xvfb); not yet on Windows with 125-175% scaling.
- Theme effect redone, cleaner: the banner lights are now three layers of depth. Large soft bubbles (a faint disc with a thin ring of light) drift slowly upward, medium bright lights glow and pulse, and small dim dots sit in the background. They come back in from the bottom when they leave the top, and sway slightly. Applies to all effect themes (Azul galáxia, Verde, Vermelho, Amarelo, Laranja, Roxo, Rosa, Preto, Branco). Checked in screenshots on Tk 9 under Linux (Xvfb); not yet seen on Windows (Tk 8.6, screen scaling).

## 0.7.5
- Tutorials. On the first launch a welcome window offers a **Basic tutorial** (6 steps: choose the mod, language, translate, review, build/install) or an **Advanced tutorial** (17 steps that explain every part of the window and every button: mod list, list buttons, language and glossary, service and key, speed, translate/stop, redo and second pass, progress and lights, table filters, the text table and its states, the editor and marker check, apply/copy/undo, build/install/restore, glossary/tools/PO files, settings and shortcuts). The "▶ Passo a passo" button at the top is now "▶ Tutorial" and opens the same window any time. Each step draws a frame around the part it explains (it follows scrolling and resizing) and the little window moves out of the way. Steps whose part is not visible (for example the mod list in a narrow window) are skipped. Keys: Enter/→ next, ← back, Esc close. The last step of the basic tutorial has a button to jump to the advanced one. "Do not show this when the program opens" is ticked by default; unticking it brings the welcome window back next time. Texts in Portuguese, English, Spanish, Russian and Chinese (new texts not reviewed by native speakers). Text source: `kenshi_quick_translator/tutorial.py`.
- Interface polish: the mod list buttons are now a 2-column grid (before, 4 + 3 buttons in two rows were cut off in the 430 px side bar); the bottom of the review card is split into two rows (Build / Install / Restore on the bottom, Glossary / Tools / Simple mode / PO files above) so nothing is cut off in narrow windows; progress bar, status line, speed chart and service lights are one block; even spacing in the header; hand cursor on buttons and tick boxes.
- New tests: `tests/test_tutorial.py` (texts in 5 languages, same shortcuts and bullets in every language, every target the tutorial points to exists in the window, tips for the new buttons) and two real-window tests in `tests/test_window_languages.py`. Also checked with a simulated window (welcome > basic > advanced, hidden parts skipped, "do not show again" saved only on the first launch). Not opened on a real screen yet (this build environment has no Tkinter).

## Unreleased (0.7.4.x)
- New button "Abrir pasta do mod" (next to "Zerar tradução" and "Abrir pasta dos projetos"): opens the folder of the selected mod in Explorer with the .mod file highlighted, whether it is in kenshi/mods or in the Steam Workshop folder. With no mod selected it uses the open mod. Tested with a stub (the right path and command are chosen); not tried on a real Windows yet.
- New presets "Comida e bebida" (food, drinks, drugs, including one-word names like Bread) and "Cenários de início de jogo" (the new-game start-off names) for the official languages, built from the official Kenshi files you sent (Japanese and Russian have no food names in the official files, so only the scenarios were added). They are not selected by default.
- Error log on disk: `erros.log` in the program's data folder (next to the translation memory). It records window errors, background errors and, with Python's fault handler, crashes of Python itself that close the program without a message. It restarts at 300 KB (the old one becomes `erros.antigo`). "Copy error report" now shows its path.
- At the end of a translation the summary says how many texts use the glossary and how many had a glossary term but did not use it.
- The texts added since 0.7.3 (glossary per language window, consistency, memory, summary, errors) are now translated to English, Spanish, Russian and Chinese. Translations written by the author's assistant, not reviewed by native speakers.
- Tools > "Conferir consistência": lists the same source text translated in different ways (button to use the most common version everywhere) and translations that do not use the glossary form (button to mark them "Conferir"). Tools > "Memória de tradução": shows the size of the translation memory (already shared by all mods) and exports/imports it as a .json file. Logic tested; the buttons were not opened on a real screen.
- The window no longer closes when you change "Idioma do mod" (source language): errors in that step now show as a message in the status bar and are saved for "Copy error report"; the error handler also no longer fails in the windowed .exe (which has no console). The exact original cause was not found, so this is a safety net.
- New real-window tests (`tests/test_window_languages.py`, run with `testar-janela.bat`): they open the program, change the mod language and the target language many times, and fail if any error happens. They are skipped on computers with no screen or no tkinter. Not run on a real screen by the author yet.
- One glossary per target language. Switching "Translate to" now switches the glossary too (`glossario.json` stays for Português (Brasil); other languages use `glossario.<code>.json`), so Portuguese terms are never used when translating to Spanish. Each glossary file records its language. When the chosen language has no glossary yet, a window asks what to do: create it with the official Kenshi names of that language (cities, factions, named characters), choose presets, or translate without a glossary. It appears when you change the target language and again before translating, until you decide. Languages with no official Kenshi translation get the "keep original names" preset. The main window shows which glossary is active and how many terms it has; the Glossary window shows the language in its title. Existing `glossario.json` files keep working as the Português (Brasil) glossary. The new window was tested only with a stubbed Tk, not on a real screen, and its text is not translated to the other interface languages yet.
- Fixed the version in pyproject.toml (it still said 0.7.1).
- Glossary presets with the official Kenshi names in Brazilian Portuguese (from the game's own pt-BR translation): cities and places (159 terms), factions (72) and named characters (73). In Glossary, click "Kenshi presets…", tick what you want and add. Terms you already have are kept unless you tick the overwrite option. Names the game leaves unchanged are added as "keep as is". Terms that are also ordinary English words (e.g. Wolves, Nowhere) are left out on purpose. The character list is automatic and approximate: check it. `tools/build_presets.py` rebuilds the presets from a Kenshi `pt_BR` folder. Window tested only with a stubbed Tk, not on a real screen.
- New program icon (face with laurel wreath). Each size of the .ico (16 to 256, including 28, 30, 36 and 42 for 125% to 175% screen scaling) is drawn separately with flat colors, thicker outlines and a larger eye at small sizes, so the taskbar icon is no longer shrunk by Windows. Not tested on Windows yet.

## 0.7.1
- New setting "Dependent mode: also bring tips.txt and names*.txt" (on by default): besides the .mod and the image, the translation folder gets the translated tips.txt and the name lists (namesM/namesF/namesMF.txt, copied untranslated). The original mod's folder is never touched. Not yet tested in-game whether Kenshi reads them from there.
- Settings: the gray explanation lines are gone; each option now shows its explanation in a tooltip when the mouse rests on it (tooltips wait half a second).
- Themes renamed (Aurora green, Supernova red, Solar yellow, Twilight orange, Nebula purple, Quasar pink) and two new gradient themes: Eclipse black and Lunar white (a light one with dark text).
- Names in another alphabet (Dependent mode): when the `namesM/namesF/namesMF.txt` being brought along have Russian, Greek, Japanese (kana), Korean or Chinese/kanji letters and the target language doesn't use that alphabet, they are converted to Latin letters (Шаку → Shaku, Джимбад → Jimbad, 김민수 → Gimminsu, 张伟 → Zhang Wei). Files already in Latin letters are left byte-for-byte. New setting (on by default); the install message lists which files were converted. Chinese/kanji use the optional `unidecode` package; without it those lines stay as they were. The original mod's files are never changed.
- Polish: the animated banner now has an aurora-like gradient (soft bands of light across the width, redrawn only when you stop resizing) and a glowing bottom edge.
- Dark colour themes: less saturation on yellow, orange and green so they no longer look muddy; highlighted buttons (white text) are darkened until their contrast is at least 4.6:1 in every theme; the light theme's warning colour is a bit darker for contrast.
- Tooltips wait half a second and disappear when you click or the widget goes away.
- Version bumped to 0.7.1.

## 0.7.0
- Safe mode (on by default, suggested by Kakrain): the extra text fields are only taken from record types the player actually sees (dialogue, dialogue lines, dialogue packages, tutorials, items, factions, characters...). Animations, animation files, effects and other technical records are left untouched, since translating them can corrupt the mod. The log lists what was skipped by record type.
- Setting "Safe mode…" in Settings to turn it off (old behaviour).
- Settings window redesigned: bigger, split into sections (Appearance, Notices, Translation, Installing in the game, Data and credits), with a note under each option, a fixed Save/Cancel bar and scrolling on small screens. Fixes the safe-mode option being hidden behind the buttons.
- New themes with an animated banner: Galaxy blue, Green, Red, Yellow, Orange, Purple and Pink. The top banner has a glow rising from the bottom and soft floating lights. Pauses when the window is minimized.
- Fix: *Install in the game* no longer freezes the window ("Not responding"). It now runs in the background with a progress box, so big mods can be installed. In Dependent mode it also never touches the original mod's folder (no `locale` swap, no `.txt` changes).
- Fix: in Dependent mode the original mod's folder is no longer copied (only its images). Copying it duplicated `RE_Kenshi.json` and the plugin DLLs of mods such as Second Life of Kenshi, which could crash the game. Settings now advise Dependent for mods with plugins.
- Fix: the window background no longer flashes light when the program opens in a dark theme.

## 0.6.9
- Fix: saving a project no longer fails with "Access denied" (WinError 5) when antivirus, a cloud-sync tool or another copy of the program holds the file for a moment. It retries and, if needed, writes directly.

## 0.6.8
- Mods with a `locale` folder: on install, build a full language pack from `Kenshi/locale/<language>` and merge the mod's own phrases (translated); original kept as `locale_off`, undone by *Restore the original*. Fixes menus, dialogue and start screen in English with mods such as Project Kathun.
- Works for any target language the game ships a pack for (`pt_BR`, `ru_RU`, `zh_CN`…), copying fonts too; exact folder name wins when several match.
- Setting: "If the mod has a locale folder: build the full language…" (on by default).
- Removed the "scan the mod" window (not needed).

## 0.6.5
- Translate `tips.txt` and other sentence lists in the mod folder on install (setting, on by default); name lists untouched; original kept as `<file>.original`.

## 0.6.4
- Collect text-only edits to base-game records (dialogue, descriptions) made by a mod; never the record names.

## 0.6.3
- Renamed to Kenshi Quick Translator.

---

# Novidades (português)

## 0.7.0
- Modo seguro (ligado por padrão, dica do Kakrain): os campos de texto extras só vêm de tipos de registro que o jogador vê (diálogos, falas, pacotes de diálogo, tutoriais, itens, facções, personagens...). Animações, arquivos de animação, efeitos e outros registros técnicos ficam intactos, porque traduzir ali pode corromper o mod. O relatório mostra o que foi deixado de fora, por tipo de registro.
- Opção "Modo seguro…" em Configurações para desligar (comportamento antigo).
- Janela de Configurações refeita: maior, em seções (Aparência, Avisos, Tradução, Instalação no jogo, Dados e créditos), com explicação embaixo de cada opção, botões Salvar/Cancelar fixos e rolagem em telas pequenas. Corrige a opção do modo seguro que ficava escondida atrás dos botões.
- Novos temas com faixa animada: Azul galáxia, Verde, Vermelho, Amarelo, Laranja, Roxo e Rosa. A faixa do topo tem um brilho subindo de baixo e luzinhas planando. Pausa quando a janela está minimizada.
- Correção: *Instalar no jogo* não trava mais a janela ("Não está respondendo"). Agora roda em segundo plano, com uma caixa de progresso, então mods grandes podem ser instalados. No modo Dependente também nunca mexe na pasta do mod original (sem trocar a `locale`, sem alterar `.txt`).
- Correção: no modo Dependente a pasta do mod original não é mais copiada (só as imagens). Copiar duplicava o `RE_Kenshi.json` e as DLLs de plugins de mods como o Second Life of Kenshi, o que podia derrubar o jogo. As Configurações agora recomendam Dependente para mods com plugins.
- Correção: o fundo da janela não pisca claro ao abrir o programa em tema escuro.

## 0.6.9
- Correção: salvar o projeto não falha mais com "Acesso negado" (WinError 5) quando o antivírus, a sincronização na nuvem ou outra cópia do programa segura o arquivo por um instante. Ele tenta de novo e, se preciso, grava direto.

## 0.6.8
- Mods com pasta `locale`: ao instalar, monta o pacote de idioma completo a partir de `Kenshi/locale/<idioma>` e junta as frases do mod (traduzidas); a original fica como `locale_off` e **Restaurar o original** desfaz. Corrige menu, diálogos e tela de início em inglês em mods como o Project Kathun.
- Funciona para qualquer idioma que o jogo tenha em pacote (`pt_BR`, `ru_RU`, `zh_CN`…), copiando também as fontes; se mais de uma pasta servir, vence a de nome igual.
- Opção: "Se o mod tem pasta locale: montar o idioma completo…" (ligada por padrão).
- Removida a janela "Vasculhar o mod" (não é necessária).

## 0.6.5
- Traduz `tips.txt` e outras listas de frases da pasta do mod ao instalar (opção, ligada por padrão); listas de nomes ficam como estão; original guardado como `<arquivo>.original`.

## 0.6.4
- Coleta edições só de texto em registros do jogo base (falas, descrições) feitas por um mod; nunca o nome dos registros.

## 0.6.3
- Renomeado para Kenshi Quick Translator.
