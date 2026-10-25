# Changelog

## 0.7.0
- Safe mode (on by default, suggested by Kakrain): the extra text fields are only taken from record types the player actually sees (dialogue, dialogue lines, dialogue packages, tutorials, items, factions, characters...). Animations, animation files, effects and other technical records are left untouched, since translating them can corrupt the mod. The log lists what was skipped by record type.
- Setting "Safe mode…" in Settings to turn it off (old behaviour).
- Settings window redesigned: bigger, split into sections (Appearance, Notices, Translation, Installing in the game, Data and credits), with a note under each option, a fixed Save/Cancel bar and scrolling on small screens. Fixes the safe-mode option being hidden behind the buttons.
- New themes with an animated banner: Galaxy blue, Green, Red, Yellow, Orange, Purple and Pink. The top banner has a glow rising from the bottom and soft floating lights. Pauses when the window is minimized.
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
